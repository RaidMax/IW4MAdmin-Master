from os import environ

from flask import render_template

from ecommerce import app
from ecommerce.integrations.logic.plan_logic import PlanLogic


@app.route('/')
def home():
    return render_template('home.html', page_id='home')


@app.route('/plugins')
def plugins():
    plan_logic = PlanLogic()
    return render_template('plugins.html', plans=plan_logic.get_plans(), cb_project=environ['CHARGEBEE_PROJECT'],
                           page_id='plugins')


@app.route('/setup')
def setup():
    return render_template('setup.html', page_id='setup')


@app.route('/terms')
def terms():
    return render_template('terms.html', page_id='terms')

