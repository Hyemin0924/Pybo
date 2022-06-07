from flask import Blueprint, render_template, request, url_for, g, flash
from pybo.models import Question, Answer, User, question_voter
from ..forms import QuestionForm, AnswerForm
from datetime import datetime
from werkzeug.utils import redirect
from .. import db
from pybo.views.auth_views import login_required
from sqlalchemy import func

bp = Blueprint('question', __name__, url_prefix='/question')
@bp.route('/list/')
def _list():
    page = request.args.get('page', type=int, default=1)
    kw = request.args.get('kw', type=str, default='')
    se = request.args.get('se', type=str, default='all')
    question_list = Question.query.order_by(Question.create_date.desc())
    if kw:
        search = '%%{}%%'.format(kw)
        sub_query = db.session.query(Answer.question_id, Answer.content, User.username) \
            .join(User, Answer.user_id == User.id).subquery()
        if se == 'all':
            question_list = question_list \
                .join(User) \
                .outerjoin(sub_query, sub_query.c.question_id == Question.id) \
                .filter(Question.subject.ilike(search) |  # 질문제목
                        User.username.ilike(search) |  # 질문작성자
                        sub_query.c.content.ilike(search)  # 답변내용
                        ) \
                .distinct()
        elif se == 'us':
            question_list = question_list \
                .join(User) \
                .outerjoin(sub_query, sub_query.c.question_id == Question.id) \
                .filter(User.username.ilike(search)
                        ) \
                .distinct()
        elif se == 'sub':
            question_list = question_list \
                .join(User) \
                .outerjoin(sub_query, sub_query.c.question_id == Question.id) \
                .filter(Question.subject.ilike(search)
                        ) \
                .distinct()
        elif se == 'aco':
            question_list = question_list \
                .join(User) \
                .outerjoin(sub_query, sub_query.c.question_id == Question.id) \
                .filter(sub_query.c.content.ilike(search)
                        ) \
                .distinct()

    sub_query = db.session.query(question_voter.c.question_id, func.count('*').label('num_voter')).group_by(question_voter.c.question_id).subquery()
    question_best = Question.query.outerjoin(sub_query,Question.id == sub_query.c.question_id).order_by(sub_query.c.num_voter.desc(),Question.create_date.desc())
    question_best = question_best.paginate(page, per_page=2)
    question_list = question_list.paginate(page, per_page=5)
    return render_template('question/question_list.html', question_list=question_list, question_best=question_best, page=page, kw=kw)\


@bp.route('/Mylist/')
def Mylist():
    page = request.args.get('page', type=int, default=1)
    question_listU = Question.query.order_by(Question.create_date.desc())
    question_listU = question_listU.join(User).filter(User.username == g.user.username)
    question_listU = question_listU.paginate(page, per_page=5)
    return render_template('question/question_U.html', question_list=question_listU)

@bp.route('/Myanswer/')
def Myanswer():
    page = request.args.get('page', type=int, default=1)
    question_a_listU = Question.query.order_by(Question.create_date.desc())
    sub_query = db.session.query(Answer.question_id, Answer.content, User.username) \
        .join(User, Answer.user_id == User.id).subquery()
    question_a_listU = question_a_listU.join(User).outerjoin(sub_query, sub_query.c.question_id == Question.id).filter(
        sub_query.c.username == g.user.username)
    question_a_listU = question_a_listU.paginate(page, per_page=5)
    return render_template('question/question_U.html', question_list=question_a_listU)

@bp.route( '/detail/<int:question_id>/')
def detail(question_id):
    form = AnswerForm()
    question = Question.query.get_or_404(question_id)
    return render_template('question/question_detail.html', question=question, form=form)
@bp.route('/create/', methods=('GET','POST'))
@login_required
def create():
    form = QuestionForm()
    if request.method == 'POST' and form.validate_on_submit():
        question = Question(subject=form.subject.data, content=form.content.data, create_date=datetime.now(), user=g.user)
        db.session.add(question)
        db.session.commit()
        return redirect(url_for('main.index'))
    return render_template('question/question_form.html', form=form)

@bp.route('/modify/<int:question_id>', methods=('GET', 'POST'))
@login_required
def modify(question_id):
    question = Question.query.get_or_404(question_id)
    if g.user != question.user:
        flash('수정권한이 없습니다')
        return redirect(url_for('question.detail', question_id=question_id))
    if request.method == 'POST':  # POST 요청
        form = QuestionForm()
        if form.validate_on_submit():
            form.populate_obj(question)
            question.modify_date = datetime.now()  # 수정일시 저장
            db.session.commit()
            return redirect(url_for('question.detail', question_id=question_id))
    else:  # GET 요청
        form = QuestionForm(obj=question)
    return render_template('question/question_form.html', form=form)

@bp.route('/delete/<int:question_id>')
@login_required
def delete(question_id):
    question = Question.query.get_or_404(question_id)
    if g.user != question.user:
        flash('삭제권한이 없습니다')
        return redirect(url_for('question.detail', question_id=question_id))
    db.session.delete(question)
    db.session.commit()
    return redirect(url_for('question._list'))

i=[]
@bp.route('/vote/<int:question_id>/')
@login_required
def vote(question_id):
    _question = Question.query.get_or_404(question_id)
    if g.user == _question.user:
        flash('본인이 작성한 글은 추천할 수 없습니다')

    else:
        for i in range(0, len(_question.voter_U)):
            if g.user == _question.voter_U[i]:
                _question.voter_U.remove(g.user)
        _question.voter.append(g.user)
        db.session.commit()
    return redirect(url_for('question.detail', question_id=question_id))


@bp.route('/vote_U/<int:question_id>/')
@login_required
def vote_U(question_id):
    _question = Question.query.get_or_404(question_id)
    if g.user == _question.user:
        flash('본인이 작성한 글은 비추천할 수 없습니다')
    else:
        for i in range(0,len(_question.voter)):
            if g.user == _question.voter[i]:
                _question.voter.remove(g.user)
        _question.voter_U.append(g.user)
        db.session.commit()
    return redirect(url_for('question.detail', question_id=question_id))