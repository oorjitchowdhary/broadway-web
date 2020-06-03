from flask import *
from firebase_admin import firestore
from flask_login import login_required, current_user

from broadway.db import db

bp = Blueprint('quiz', __name__)

@bp.route('/quiz', methods=['GET', 'POST'])
@login_required
def quiz():
    questions = db.collection(u'quiz').stream()
    user_doc = db.collection(u'users').document(current_user.username)
    user_correct_answers = user_doc.get().to_dict()['num_of_correct_answers']

    if user_correct_answers >= 3:
        flash("<i class='fa fa-exclamation-circle'></i>\tYou've already won the free tickets.", 'flash-success')
        return redirect(url_for('index'))

    elif user_correct_answers == 0:
        if request.method == 'POST':
            d = {}
            num_correct_answers = 0
            for q in questions:
                qid = q.id
                d = {qid: request.form[qid]}
                for i in d.keys():
                    q_doc = db.collection(u'quiz').document(i).get().to_dict()
                    if d[i] == q_doc['correct_answer']:
                        num_correct_answers += 1
            user_doc.update({u'num_of_correct_answers': num_correct_answers})

            if num_correct_answers >= 3:
                flash(f"<i class='fa fa-check circle'></i>\tCongratulations! You've just won 2 free tickets. Check your email for more details.", 'flash-success')
                return redirect(url_for('index'))
            else:
                flash(f"<i class='fa fa-exclamation-circle'></i>\tHard luck! You answered {num_correct_answers} questions correctly. Free tickets are given to people who got 3 questions or more correct.")
                return redirect(url_for('index'))

    else:
        flash("<i class='fa fa-exclamation-circle'></i>\tYou've already attempted this quiz once.", 'flash-alert')
        return redirect(url_for('index'))

    return render_template('quiz.html', questions=questions)