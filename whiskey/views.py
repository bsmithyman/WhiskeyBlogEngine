from flask import render_template, flash, redirect, session, url_for, request, g
from flask.ext.login import login_user, logout_user, current_user, login_required
from whiskey import app, mongo, cloud, boto, cache, s3, gfm
from helper import *
from models import User, Post
import models
from bson.objectid import ObjectId
import misaka

# ------------------------------------------------------------------------
# HTTP Errors

@app.errorhandler(404)
@cache.cached(3600)
def page_not_found (error):
    pageinfo = {
        'title':        '404',
        'heading':      'you are lost',
    }
    pageinfo = generate_pageinfo(pageinfo)
    return render_template('404.html', pageinfo = pageinfo, models = models), 404

@app.errorhandler(500)
def internal_error (error):
    pageinfo = {
        'title':        '500',
        'heading':      'computer over',
    }
    pageinfo = generate_pageinfo(pageinfo)
    # Clean up DB, etc.
    return render_template('500.html', pageinfo = pageinfo, models = models), 500

# ------------------------------------------------------------------------
# Normal Views

@app.route('/')
@cache.cached(3600)
def root ():
    return redirect(url_for('index'))

@app.route('/index')
@cache.cached(300)
def index ():
    pageinfo = {
        'title':        'blog',
        'header':       'blog',
    }
    pageinfo = generate_pageinfo(pageinfo)
    posts = Post().get_all()
    if posts:
        posts = [dict(post) for post in posts]
        for post in posts:
            author = User().get({'_id': post['author']})
            post.update({'author': author}) 
        pageinfo.update({'posts': posts})
    else:
        flash('There are no posts to display')
    return render_template('index.html', pageinfo = pageinfo, models = models)

@app.route('/about')
@cache.cached(3600)
def about ():
    pageinfo = {
        'title':        'about',
        'header':       'about',
    }
    pageinfo = generate_pageinfo(pageinfo)
    return render_template('about.html', pageinfo = pageinfo, models = models)

@app.route('/animtest')
def animtest ():
    pageinfo = {
        'ajax':         True,
        'title':        'animtest',
        'heading':      'animation test',
    }
    pageinfo = generate_pageinfo(pageinfo)
    pageinfo = add_animheader(pageinfo)
    return render_template('animtest.html', pageinfo = pageinfo, models = models)

@app.route('/profile/<nickname>')
@cache.cached(300)
def profile (nickname):
    pageinfo = {
        'title':        'profile',
        'heading':      'user profile',
    } 
    pageinfo = generate_pageinfo(pageinfo)
    user = User().get({'nickname': nickname})
    if user:
      pageinfo.update({'user': user, 'heading': nickname})
    else:
      flash('User {0} not found'.format(nickname))
    return render_template('profile.html', pageinfo = pageinfo, models = models)

@app.route('/users')
@cache.cached(3600)
def users ():
    pageinfo = {
        'title':        'users',
        'heading':      'site users',
    }
    pageinfo = generate_pageinfo(pageinfo)
    users = User().get_all()
    if users:
        pageinfo.update({'users': User().get_all()})
    else:
        flash('There are no users')
    return render_template('users.html', pageinfo = pageinfo, models = models)

@app.route('/post/<identifier>')
@cache.cached(300)
def post (identifier):
    pageinfo = {
        'title':        'post',
        'heading':      'view post',
    }
    pageinfo = generate_pageinfo(pageinfo)
    # This is probably dangerous; TODO: fix Post URL scheme.
    post = Post().get({'_id': ObjectId(identifier)})
    if post:
        post = dict(post)
        augment = {
            'html':         misaka.html(gfm.gfm(post['content'])),
            'author':         User().get({'_id': post['author']}),
        }
        post.update(augment)
        pageinfo.update({'post': post, 'heading': post['title'], 'title': post['title']})
    else:
        flash('Post not found: {0}')
    return render_template('post.html', pageinfo = pageinfo, models = models)

# ------------------------------------------------------------------------
# User Authentication

@app.route('/login', methods = ['GET', 'POST'])
def login ():
    pageinfo = {
        'title':        'login',
        'heading':      'login required',
    }
    pageinfo = generate_pageinfo(pageinfo)
    return render_template('login.html', pageinfo = pageinfo, models = models)

@app.route('/logout')
def logout ():
    # logout_user()
    return redirect(url_for('index'))

# ------------------------------------------------------------------------
# Test Suite

@app.route('/test')
@login_required
def testsuite ():

    testfunc = lambda x: x**2
    testvalue = 42
    testdict = {'author': 'Linus', 'title': 'Linux', 'category': 'OS'}

    jid = cloud.call(testfunc, testvalue)
    cache.set('testvalue', testvalue, timeout = 5 * 60)

    lines = ['<html><head><title>Test Suite</title></head><body><pre>']
    hline = '\n' + '-'*80 + '\n'

    lines.append(hline)

    lines.append('Testing S3\n')
    lines.append('Listing all buckets:')
    for bucket in s3.get_all_buckets():
        lines.append('\t{}'.format(bucket.name))

    lines.append(hline)

    testvalue1 = cache.get('testvalue')
    lines.append('Testing Cache\n')
    lines.append('cache.set(\'testvalue\', {0}, timeout)'.format(testvalue))
    lines.append('cache.get(\'testvalue\') --> {}'.format(testvalue1))

    lines.append(hline)

    lines.append('Testing Database\n')

    collection = mongo.db.test_collection
    id = collection.insert(testdict)

    lines.append('testdict = {!r}'.format(testdict))
    lines.append('collection.insert(testdict) --> {}'.format(id))
    lines.append('db.collection_names() --> {}'.format(mongo.db.collection_names()))
    lines.append('collection.find_one() --> {}'.format(collection.find_one()))

    lines.append(hline)

    lines.append('Testing PiCloud\n')
    
    lines.append('\tRunning job: {}'.format(jid))
    result = cloud.result(jid)
    lines.append('\tResult: {0} * {0} = {1}'.format(testvalue, result))

    lines.append(hline)

    lines.append('</pre></body></html>')
    return '\n'.join(lines)

@app.route('/forceerror')
def forceerror ():
    raise Exception   

@app.route('/modeltest')
@login_required
def modeltest ():
    a = User()
    a['nickname'] =     'brendan'
    a['fullname'] =     'Brendan Smithyman'
    a['email'] =        'brendan@bitsmithy.net'
    a['ghlogin'] =      'bsmithyman'
    a['profile'] =      'This is a bio about me.'
    a.save()

    beninfo = {
        'nickname':     'ben',
        'fullname':     'Ben Postlethwaite',
        'email':        'post.ben.here@gmail.com',
        'ghlogin':      'bpostlethwaite',
        'profile':      'This is a bio about Ben.',
    }
         
    b = User(beninfo)
    b.save()

    a1 = User().get({'nickname': 'ben'})
    b1 = User().get_all({'email': a['email']})

    lines = []

    for eadict in [a1, b1[0]]:
        lines.append('{0!r}'.format(eadict))
        for key in eadict:
            lines.append('\t\'{0}\' -> {1}'.format(key, eadict[key]))
        lines.append('')

    return '\n'.join(lines)
