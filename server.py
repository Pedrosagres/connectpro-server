#!/usr/bin/env python3
# ============================================================
#  ConnectPro Server v2.0  —  WebRTC Signaling
# ============================================================

from flask import Flask, request, jsonify
import threading, time, random

app = Flask(__name__)

_sessions = {}
_lock     = threading.Lock()
TTL       = 3600


def _cleanup():
    while True:
        time.sleep(60)
        now = time.time()
        with _lock:
            expired = [k for k, v in _sessions.items() if v['expires'] < now]
            for k in expired:
                del _sessions[k]

threading.Thread(target=_cleanup, daemon=True).start()


def _gen_code():
    with _lock:
        for _ in range(100):
            code = str(random.randint(100000, 999999))
            if code not in _sessions:
                return code
    return str(random.randint(100000, 999999))


@app.route('/ping')
def ping():
    return jsonify({'status': 'ok'})


@app.route('/session/create', methods=['POST'])
def session_create():
    data  = request.get_json(force=True)
    offer = data.get('offer')
    if not offer:
        return jsonify({'error': 'offer required'}), 400
    code = _gen_code()
    with _lock:
        _sessions[code] = {
            'offer':      offer,
            'answer':     None,
            'ice_agent':  [],
            'ice_viewer': [],
            'expires':    time.time() + TTL,
        }
    return jsonify({'code': code})


@app.route('/session/<code>/ice_agent', methods=['POST'])
def post_ice_agent(code):
    data = request.get_json(force=True)
    with _lock:
        if code not in _sessions:
            return jsonify({'error': 'not found'}), 404
        _sessions[code]['ice_agent'].append(data.get('candidate'))
    return jsonify({'ok': True})


@app.route('/session/<code>/offer', methods=['GET'])
def get_offer(code):
    with _lock:
        s = _sessions.get(code)
    if not s:
        return jsonify({'error': 'invalid code'}), 404
    return jsonify({'offer': s['offer']})


@app.route('/session/<code>/answer', methods=['POST'])
def post_answer(code):
    data = request.get_json(force=True)
    with _lock:
        if code not in _sessions:
            return jsonify({'error': 'not found'}), 404
        _sessions[code]['answer'] = data.get('answer')
    return jsonify({'ok': True})


@app.route('/session/<code>/ice_viewer', methods=['POST'])
def post_ice_viewer(code):
    data = request.get_json(force=True)
    with _lock:
        if code not in _sessions:
            return jsonify({'error': 'not found'}), 404
        _sessions[code]['ice_viewer'].append(data.get('candidate'))
    return jsonify({'ok': True})


@app.route('/session/<code>/answer', methods=['GET'])
def get_answer(code):
    with _lock:
        s = _sessions.get(code)
    if not s:
        return jsonify({'error': 'not found'}), 404
    return jsonify({'answer': s['answer']})


@app.route('/session/<code>/ice_agent', methods=['GET'])
def get_ice_agent(code):
    with _lock:
        s = _sessions.get(code)
    if not s:
        return jsonify({'error': 'not found'}), 404
    return jsonify({'candidates': s['ice_agent']})


@app.route('/session/<code>/ice_viewer', methods=['GET'])
def get_ice_viewer(code):
    with _lock:
        s = _sessions.get(code)
    if not s:
        return jsonify({'error': 'not found'}), 404
    return jsonify({'candidates': s['ice_viewer']})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
