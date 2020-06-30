import re
from .. import app

@app.template_filter()
def regex_replace(s, find, replace):
    return re.sub(find, replace, s)