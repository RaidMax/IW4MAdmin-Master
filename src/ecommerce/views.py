from os import environ

from flask import render_template

from ecommerce.integrations.logic.plan_logic import PlanLogic
from master import app


@app.route('/store')
def store():
    plan_logic = PlanLogic()
    return render_template('ecommerce/home.html', plans=plan_logic.get_plans(), cb_project=environ['CHARGEBEE_PROJECT'])


@app.route('/store/manage')
def manage():
    return render_template('ecommerce/manage.html')
