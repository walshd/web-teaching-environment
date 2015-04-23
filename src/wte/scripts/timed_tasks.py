# -*- coding: utf-8 -*-
u"""
###########################################################
:mod:`wte.scripts.timed_tasks` -- Script to run timed tasks
###########################################################

The :mod:`~wte.scripts.timed_tasks` module provides the functionality for
running :class:`~wte.models.TimedTask`. Only a single instance of it should
ever be run as otherwise it is possible that tasks are run multiple times.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import logging
import transaction

from pyramid.paster import (get_appsettings, setup_logging)
from random import randint
from sqlalchemy import (engine_from_config, and_, func)
from threading import Thread

from wte.models import (DBSession, Base, TimedTask, Part)


def init(subparsers):
    u"""Initialises the :class:`~argparse.ArgumentParser`, adding the
    "run-timed-tasks" command that runs :func:`~wte.scripts.timed_tasks.run_timed_tasks`.
    """
    parser = subparsers.add_parser('run-timed-tasks', help='Run all timed tasks that are due')
    parser.add_argument('configuration', help='WTE configuration file')
    parser.set_defaults(func=run_timed_tasks)


def run_timed_tasks(args):
    u"""Runs all timed tasks where the timestamp is in the past and the status is "ready".
    
    All :class:`~wte.models.TimedTask` that are to be run are given a unique "run-{random-number}"
    ``status`` to uniquely identify them for this run. Individual task runners are then
    responsible for setting that status to "completed" after the task completes successfully
    or to "failed" if it failed.
    
    All task runners are run in independent :class:`threading.Thread`\ s. After all
    :class:`~threading.Thread` complete, any :class:`~wte.models.TimedTask` that still have
    the unique "run-{random-number}" status are automatically set to the "failed" status. 
    """
    settings = get_appsettings(args.configuration)
    setup_logging(args.configuration)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    dbsession = DBSession()
    tasks = dbsession.query(TimedTask).filter(and_(TimedTask.timestamp <= func.now(),
                                                   TimedTask.status == u'ready'))
    rnd = randint(0, 1000000)
    with transaction.manager:
        tasks.update({TimedTask.status: u'running-%i' % (rnd)}, synchronize_session=False)
    tasks = dbsession.query(TimedTask).filter(TimedTask.status == u'running-%i' % (rnd))
    task_count = tasks.count()
    if task_count > 0:
        logging.getLogger('wte').info('Running %i tasks' % (task_count))
        threads = []
        for task in tasks:
            if task.name == 'change_status':
                threads.append(Thread(None, target=run_change_status, args=(task.id,)))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        dbsession.flush()
        failed_count = tasks.count()
        if failed_count > 0:
            logging.getLogger('wte').error('%i tasks failed' % (failed_count))
        else:
            logging.getLogger('wte').info('All tasks completed')
        with transaction.manager:
            tasks.update({TimedTask.status: u'failed'})


def run_change_status(task_id):
    u"""Run the status change task for the :class:`~wte.models.TimedTask` with the
    id ``task_id``. It changes the :class:`~wte.models.TimedTask`\ s status to the
    value of the "target_status" key in the :attr:`~wte.models.TimedTask.options`.
    """
    dbsession = DBSession()
    task = dbsession.query(TimedTask).filter(TimedTask.id == task_id).first()
    if task:
        part = dbsession.query(Part).filter(Part.id == task.part_id).first()
        if part and 'target_status' in task.options:
            with transaction.manager:
                dbsession.add(part)
                dbsession.add(task)
                part.status = task.options['target_status']
            with transaction.manager:
                dbsession.add(task)
                task.status = 'completed'
