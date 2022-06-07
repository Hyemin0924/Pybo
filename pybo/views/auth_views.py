from flask import Blueprint, url_for, render_template, flash, request, session, g, Flask
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import redirect, secure_filename
import functools
from pybo import db
from pybo.forms import UserCreateForm, UserLoginForm, UpdateAccountForm
from pybo.models import Question, User, Answer
import os

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/signup/', methods=('GET', 'POST'))
def signup():
    form = UserCreateForm()
    if request.method == 'POST' and form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if not user:
            user = User(username=form.username.data,
                        password=generate_password_hash(form.password1.data),
                        email=form.email.data)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('main.index'))
        else:
            flash('이미 존재하는 사용자입니다.')
    return render_template('auth/signup.html', form=form)

@bp.route('/login/', methods=('GET', 'POST'))
def login():
    form = UserLoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        error = None
        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            error = "존재하지 않는 사용자입니다."
        elif not check_password_hash(user.password, form.password.data):
            error = "비밀번호가 올바르지 않습니다."
        if error is None:
            session.clear()
            session['user_id'] = user.id
            _next = request.args.get('next', '')
            if _next:
                return redirect(_next)
            else:
                return redirect(url_for('main.index'))
        flash(error)
    return render_template('auth/login.html', form=form)

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = User.query.get(user_id)


@bp.route('/logout/')
def logout():
    session.clear()
    return redirect(url_for('main.index'))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            _next = request.url if request.method == 'GET' else ''
            return redirect(url_for('auth.login', next=_next))
        return view(*args, **kwargs)
    return wrapped_view


@bp.route('/account/', methods=('GET', 'POST'))
def account():
    form = UpdateAccountForm()
    if request.method == 'POST' and form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if not user:
            g.user.username = form.username.data
            db.session.commit()
            return redirect(url_for('main.index'))
        else:
            flash('이미 존재하는 아이디입니다.')
    page = request.args.get('page', type=int, default=1)
    question_listU = Question.query.order_by(Question.create_date.desc())
    question_listU = question_listU.join(User).filter(User.username == g.user.username)
    question_listU = question_listU.paginate(page, per_page=5)
    question_a_listU = Question.query.order_by(Question.create_date.desc())
    sub_query = db.session.query(Answer.question_id, Answer.content, User.username) \
        .join(User, Answer.user_id == User.id).subquery()
    question_a_listU = question_a_listU.join(User).outerjoin(sub_query, sub_query.c.question_id == Question.id).filter(sub_query.c.username == g.user.username)
    question_a_listU = question_a_listU.paginate(page, per_page=5)
    return render_template('auth/account.html', form=form, question_list=question_listU, question_a_list=question_a_listU)

