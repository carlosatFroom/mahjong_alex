#!/usr/bin/env python3
"""
Flask app for the Woodlands Mahjong Society practice table:
serves the game page, the game API, and the coach.
"""

import logging
import os
import secrets
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS

import coach
import security
from config import config
from content_filter import ContentFilter
from llm_providers import get_llm_provider
from mahjong.card import load_card
from mahjong.coach_facts import facts_text, hint_facts, move_feedback
from mahjong.game import Game, GameError
from store import GameStore

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

ROOT = os.path.dirname(os.path.abspath(__file__))
DIFFICULTIES = ("easy", "normal")
MAX_QUESTION_CHARS = 500


def create_app(overrides=None):
    settings = {
        "DB_PATH": config.DB_PATH, "CARD_FILE": config.CARD_FILE, "RULES_FILE": config.RULES_FILE,
        "COACH_MAX_MESSAGES": config.COACH_MAX_MESSAGES, "GAME_TTL_HOURS": config.GAME_TTL_HOURS,
        "GROQ_API_KEY": config.GROQ_API_KEY, "GROQ_MODEL": config.GROQ_MODEL,
    }
    settings.update(overrides or {})

    app = Flask(__name__, static_folder=os.path.join(ROOT, "static"), static_url_path="/static")
    app.secret_key = config.SECRET_KEY or secrets.token_hex(32)
    if not config.SECRET_KEY:
        logger.warning("FLASK_SECRET_KEY not set; sessions reset when the server restarts.")
    app.config["SESSION_COOKIE_SAMESITE"] = config.COOKIE_SAMESITE
    app.config["SESSION_COOKIE_SECURE"] = config.COOKIE_SAMESITE == "None"
    if config.ALLOWED_ORIGINS:
        CORS(app, origins=config.ALLOWED_ORIGINS, supports_credentials=True)

    card = load_card(os.path.join(ROOT, settings["CARD_FILE"]))
    with open(os.path.join(ROOT, settings["RULES_FILE"]), encoding="utf-8") as f:
        system = coach.system_prompt(card, f.read())
    store = GameStore(settings["DB_PATH"], settings["GAME_TTL_HOURS"])

    provider = content_filter = None
    if settings["GROQ_API_KEY"]:
        provider = get_llm_provider("groq", api_key=settings["GROQ_API_KEY"], model=settings["GROQ_MODEL"])
        content_filter = ContentFilter(settings["GROQ_API_KEY"])
    else:
        logger.warning("GROQ_API_KEY not set; the coach will answer with engine facts only.")

    app.extensions["mahjong"] = {"card": card, "store": store, "provider": provider}

    def session_id():
        if "sid" not in session:
            session["sid"] = uuid.uuid4().hex
            session.permanent = True
        return session["sid"]

    def load_game(game_id):
        found = store.load(game_id, session_id())
        if not found:
            return None
        return Game.from_dict(card, found[0])

    def game_payload(game_id, game, **extra):
        return jsonify({"game_id": game_id, "view": game.view_for(game.human), **extra})

    @app.before_request
    def guard():
        blocked = security.check_request(request)
        if blocked:
            return jsonify(blocked[0]), blocked[1]
        return None

    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/api/health")
    def health():
        return jsonify({"status": "healthy", "service": "mahjong-practice-table",
                        "coach": "llm" if provider else "engine-only",
                        "timestamp": datetime.now(timezone.utc).isoformat()})

    @app.route("/api/card")
    def get_card():
        return jsonify({"name": card.name, "hands": card.to_json()})

    @app.route("/api/game", methods=["POST"])
    def new_game():
        data = request.get_json(silent=True) or {}
        difficulty = data.get("difficulty", "normal")
        if difficulty not in DIFFICULTIES:
            return jsonify({"error": "Difficulty must be easy or normal."}), 400
        game = Game.new(card, difficulty=difficulty)
        game.advance()
        game_id = uuid.uuid4().hex
        store.save(game_id, session_id(), game.to_dict())
        return game_payload(game_id, game)

    @app.route("/api/game/<game_id>")
    def get_game(game_id):
        game = load_game(game_id)
        if not game:
            return jsonify({"error": "Game not found or expired."}), 404
        return game_payload(game_id, game)

    @app.route("/api/game/<game_id>/action", methods=["POST"])
    def act(game_id):
        game = load_game(game_id)
        if not game:
            return jsonify({"error": "Game not found or expired."}), 404
        action = request.get_json(silent=True) or {}
        before = game.view_for(game.human)
        try:
            game.act(action)
        except GameError as e:
            return jsonify({"error": str(e)}), 400
        except (KeyError, TypeError, ValueError):
            return jsonify({"error": "Malformed action."}), 400
        feedback = None
        if action.get("type") == "discard" and not before.get("dead"):
            feedback = move_feedback(card, before, action.get("tile"))
        store.save(game_id, session_id(), game.to_dict())
        return game_payload(game_id, game, feedback=feedback)

    @app.route("/api/game/<game_id>/coach", methods=["POST"])
    def ask_coach(game_id):
        game = load_game(game_id)
        if not game:
            return jsonify({"error": "Game not found or expired."}), 404
        data = request.get_json(silent=True) or {}
        kind = data.get("kind")
        if kind not in ("hint", "question"):
            return jsonify({"error": "kind must be hint or question"}), 400
        view = game.view_for(game.human)
        question = (data.get("text") or "").strip()[:MAX_QUESTION_CHARS]
        if kind == "question" and not question:
            return jsonify({"error": "Type a question first."}), 400

        if not store.bump_coach(game_id, settings["COACH_MAX_MESSAGES"]):
            if kind == "hint":
                return jsonify({"text": facts_text(hint_facts(card, view)), "source": "engine",
                                "note": "Coach message limit reached for this game; showing engine facts."})
            return jsonify({"error": f"The coach answers up to {settings['COACH_MAX_MESSAGES']} "
                                     "messages per game. Start a new game to ask more; "
                                     "the Hint button still works."}), 429

        if kind == "question":
            if content_filter is None:
                return jsonify({"text": "The coach can't answer typed questions right now, "
                                        "but the Hint button still works.", "source": "engine"})
            allowed, result = content_filter.filter_content(question, security.get_client_ip(request))
            if not allowed:
                return jsonify({"error": "The coach only answers Mahjong questions.",
                                "filter_stage": result.filter_stage}), 403
        return jsonify(coach.reply(provider, system, card, view, kind, question))

    @app.route("/api/stats")
    def get_stats():
        if content_filter is None:
            return jsonify({"error": "Content filter not configured"}), 503
        return jsonify(content_filter.get_system_stats())

    @app.route("/api/ip-stats/<ip>")
    def get_ip_stats(ip):
        if content_filter is None:
            return jsonify({"error": "Content filter not configured"}), 503
        return jsonify(content_filter.get_ip_stats(ip))

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=config.SERVER_HOST, port=config.SERVER_PORT,
            debug=os.getenv("FLASK_DEBUG", "False").lower() == "true")
