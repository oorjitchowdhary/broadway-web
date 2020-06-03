from flask import *
from datetime import datetime
from pytz import timezone
from flask_wtf import FlaskForm
from wtforms.fields.core import StringField
from wtforms.validators import InputRequired, Length
from wtforms.widgets.core import TextArea
from flask_login import LoginManager, login_required, current_user

from broadway.db import db

bp = Blueprint('discussion', __name__)

class NewDiscussionForm(FlaskForm):
    title = StringField('title', validators=[InputRequired(), Length(max=60)])
    description = StringField('description', validators=[Length(max=60)])
    content = StringField('content', widget=TextArea(), validators=[InputRequired()])
    
class CommentForm(FlaskForm):
    comment = StringField('comment', widget=TextArea(), validators=[InputRequired()])

@bp.route('/discuss', methods=['GET', 'POST'])
@bp.route('/discuss/', methods=['GET', 'POST'])
@login_required
def discuss():
    discussions = db.collection(u'discussions').stream()
    return render_template('discuss.html', discussions=discussions)

@bp.route('/discuss/<post_id>', methods=['GET', 'POST'])
@bp.route('/discuss/<post_id>/', methods=['GET', 'POST'])
@login_required
def discuss_post(post_id):
    discussions = db.collection(u'discussions')
    post = discussions.document(post_id).get().to_dict()
    title = post['title']
    content = post['content']
    posted_by_user = post['posted_by_user']
    posting_time = post['posting_time']

    comments_on_post = db.collection(u'comments').where(u'on_post_id', u'==', post_id).stream()

    form = CommentForm()
    if form.validate_on_submit():
        db.collection(u'comments').add({
            u'on_post_id': post_id,
            u'comment_author': current_user.username,
            u'comment': form.comment.data,
            u'likes': 0,
            u'liked_by': list(),
        })
        return redirect(url_for('discussion.discuss') + post_id)

    return render_template('post.html', title=title, content=content, posted_by_user=posted_by_user, comments_on_post=comments_on_post, form=form, time=posting_time)

@bp.route('/discuss/new', methods=['GET', 'POST'])
@login_required
def create_discussion():
    form = NewDiscussionForm()
    if form.validate_on_submit():
        db.collection(u'discussions').add({
            u'title': form.title.data,
            u'description': form.description.data,
            u'content': form.content.data,
            u'posted_by_user': current_user.username,
            u'posting_time': datetime.now(timezone('Asia/Calcutta')).strftime("%I:%M %p, %d %B %Y")
        })
        return redirect(url_for('discussion.discuss'))

    return render_template('create_discussion.html', form=form)

@bp.route('/like/<cid>', methods=['GET', 'POST'])
@login_required
def like_comment(cid):
    comment = db.collection(u'comments').document(cid)
    comment_get = comment.get().to_dict()
    likes = comment_get['likes']
    liked_by = comment_get['liked_by']
    liked_by.append(current_user.username)
    comment.update({
        u'likes': likes+1,
        u'liked_by': liked_by,
    })
    return redirect(url_for('discussion.discuss_post', post_id=comment_get['on_post_id']))

@bp.route('/unlike/<comment_id>', methods=['GET', 'POST'])
@login_required
def unlike_comment(comment_id):
    comment = db.collection(u'comments').document(comment_id)
    comment_get = comment.get().to_dict()
    likes = comment_get['likes']
    liked_by = comment_get['liked_by']
    liked_by.remove(current_user.username)
    comment.update({
        u'likes': likes-1,
        u'liked_by': liked_by,
    })
    return redirect(url_for('discussion.discuss_post', post_id=comment_get['on_post_id']))