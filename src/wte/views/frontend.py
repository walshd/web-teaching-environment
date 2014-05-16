# -*- coding: utf-8 -*-
'''
Created on 12 May 2014

@author: mhall
'''
from pyramid.view import view_config
from pywebtools.renderer import render
from sqlalchemy import and_

from wte.models import (DBSession, Module, Tutorial, Page)

@view_config(route_name='page.view')
@render({'text/html': 'page/view.html'})
def view(request):
    dbsession = DBSession()
    module = dbsession.query(Module).filter(Module.id==request.matchdict[u'mid']).first()
    tutorial = dbsession.query(Tutorial).filter(and_(Tutorial.id==request.matchdict[u'tid'],
                                                     Tutorial.module_id==request.matchdict[u'mid'])).first()
    page = dbsession.query(Page).filter(and_(Page.order==request.matchdict[u'pageno'],
                                             Page.tutorial_id==request.matchdict[u'tid'])).first()
    return {'module': module,
            'tutorial': tutorial,
            'page': page}
