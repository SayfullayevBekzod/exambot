"""IELTS WebApp — Flask API server"""
import os
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# DB import
import sys
sys.path.insert(0, os.path.dirname(__file__))
from database import (
    get_session, Subject, Question, UserResult, Flashcard,
    UserSettings, DailyStreak, PremiumSubscription, check_premium,
)

app = Flask(__name__, static_folder='webapp', static_url_path='')
CORS(app)


# === Static files ===
@app.route('/')
def index():
    return send_from_directory('webapp', 'index.html')


@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('webapp', path)


# === API ===

@app.route('/api/subjects')
def api_subjects():
    session = get_session()
    try:
        subjects = session.query(Subject).all()
        result = []
        for s in subjects:
            q_count = session.query(Question).filter_by(subject_id=s.id).count()
            result.append({
                'id': s.id,
                'name': s.name,
                'emoji': s.emoji,
                'description': s.description,
                'question_count': q_count,
            })
        return jsonify(result)
    finally:
        session.close()


@app.route('/api/questions/<int:subject_id>')
def api_questions(subject_id):
    session = get_session()
    try:
        questions = session.query(Question).filter_by(subject_id=subject_id).all()
        result = []
        for q in questions:
            result.append({
                'id': q.id,
                'text': q.text,
                'options': q.get_options(),
                'correct': q.correct_answer,
                'difficulty': q.difficulty,
            })
        return jsonify(result)
    finally:
        session.close()


@app.route('/api/results', methods=['POST'])
def api_save_result():
    data = request.json
    session = get_session()
    try:
        result = UserResult(
            user_id=data['user_id'],
            username='webapp',
            full_name='WebApp User',
            subject_id=data['subject_id'],
            score=data['score'],
            total=data['total'],
            percentage=data['percentage'],
        )
        session.add(result)
        session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        session.rollback()
        return jsonify({'ok': False, 'error': str(e)})
    finally:
        session.close()


@app.route('/api/stats')
def api_stats():
    from sqlalchemy import func

    user_id = request.args.get('user_id', 0, type=int)
    session = get_session()
    try:
        results = (
            session.query(UserResult)
            .filter_by(user_id=user_id)
            .order_by(UserResult.completed_at.desc())
            .limit(20)
            .all()
        )

        total_tests = len(results)
        avg_pct = round(sum(r.percentage for r in results) / total_tests, 1) if total_tests > 0 else 0

        if avg_pct >= 90: avg_band = '8.0+'
        elif avg_pct >= 75: avg_band = '7.0'
        elif avg_pct >= 60: avg_band = '6.0'
        elif avg_pct >= 40: avg_band = '5.0'
        else: avg_band = '4.0'

        # Streak
        streak_obj = session.query(DailyStreak).filter_by(user_id=user_id).first()
        streak = streak_obj.current_streak if streak_obj else 0

        # Subject performance bars
        subject_stats = []
        ss_raw = (
            session.query(
                UserResult.subject_id,
                func.avg(UserResult.percentage).label('avg_pct'),
            )
            .filter_by(user_id=user_id)
            .group_by(UserResult.subject_id)
            .all()
        )
        for sr in ss_raw:
            subj = session.query(Subject).get(sr.subject_id)
            if subj:
                subject_stats.append({
                    'name': subj.name,
                    'emoji': subj.emoji,
                    'avg': round(sr.avg_pct, 1),
                })

        # History
        history = []
        for r in results[:10]:
            subj = session.query(Subject).get(r.subject_id)
            history.append({
                'subject': subj.name if subj else '?',
                'emoji': subj.emoji if subj else '📚',
                'score': r.score,
                'total': r.total,
                'percentage': round(r.percentage),
                'date': r.completed_at.strftime('%d.%m.%Y') if r.completed_at else '',
            })

        # Leaderboard
        lb_raw = (
            session.query(
                UserResult.full_name,
                func.avg(UserResult.percentage).label('avg_pct'),
            )
            .group_by(UserResult.user_id)
            .order_by(func.avg(UserResult.percentage).desc())
            .limit(10)
            .all()
        )
        leaderboard = [
            {'name': r.full_name or 'Foydalanuvchi', 'avg': round(r.avg_pct, 1)}
            for r in lb_raw
        ]

        return jsonify({
            'total_tests': total_tests,
            'avg_percentage': avg_pct,
            'avg_band': avg_band,
            'streak': streak,
            'subject_stats': subject_stats,
            'history': history,
            'leaderboard': leaderboard,
        })
    finally:
        session.close()


@app.route('/api/flashcards')
def api_flashcards():
    user_id = request.args.get('user_id', 0, type=int)
    session = get_session()
    try:
        cards = session.query(Flashcard).filter_by(user_id=user_id).all()
        total = len(cards)
        mastered = sum(1 for c in cards if c.mastered)
        learning = total - mastered

        card_list = [
            {
                'id': c.id,
                'front': c.front,
                'back': c.back,
                'example': c.example or '',
                'mastered': c.mastered,
            }
            for c in cards if not c.mastered
        ]

        return jsonify({
            'total': total,
            'mastered': mastered,
            'learning': learning,
            'cards': card_list[:50],
        })
    finally:
        session.close()


@app.route('/api/flashcards/response', methods=['POST'])
def api_flashcard_response():
    data = request.json
    session = get_session()
    try:
        card = session.query(Flashcard).get(data.get('card_id'))
        if card and card.user_id == data.get('user_id'):
            if data.get('response') == 'knew':
                card.mastered = True
                session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        session.rollback()
        return jsonify({'ok': False, 'error': str(e)})
    finally:
        session.close()


@app.route('/api/premium/status')
def api_premium_status():
    user_id = request.args.get('user_id', 0, type=int)
    is_prem = check_premium(user_id)

    expiry = None
    if is_prem:
        session = get_session()
        try:
            sub = (
                session.query(PremiumSubscription)
                .filter_by(user_id=user_id, is_active=True)
                .order_by(PremiumSubscription.end_date.desc())
                .first()
            )
            if sub:
                expiry = sub.end_date.strftime('%d.%m.%Y')
        finally:
            session.close()

    return jsonify({
        'is_premium': is_prem,
        'expiry': expiry,
    })


if __name__ == '__main__':
    from database import init_db
    init_db()
    port = int(os.environ.get("PORT", 8080))
    print(f"🌐 WebApp server running on port {port}")
    app.run(host='0.0.0.0', port=port)
