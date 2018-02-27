#!/usr/bin/env python

from copy import deepcopy

import time
import datetime
import os
import os.path as op
import random as rnd
import string
import json
import sys

import boutiques as bosh

from clowdr import utils


def consolidate(tool, invocation, clowdrloc, dataloc, **kwargs):
    # TODO: document
    ts = time.time()
    dt = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    randx = "".join(rnd.choices(string.ascii_uppercase + string.digits, k=8))
    modif = "{}-{}".format(dt, randx)

    # Scrub inputs
    tool = utils.truepath(tool)
    invocation = utils.truepath(invocation)
    clowdrloc = utils.truepath(clowdrloc)
    dataloc = utils.truepath(dataloc)

    # Initialize task dictionary
    taskdict = {}
    with open(tool) as fhandle:
        toolname = json.load(fhandle)["name"].replace(' ', '-')
    taskloc = op.join(clowdrloc, modif, 'clowdr')
    os.makedirs(taskloc)

    taskdict["taskloc"] = op.join(clowdrloc, modif, toolname)
    taskdict["dataloc"] = [dataloc]
    taskdict["invocation"] = utils.get(invocation, taskloc)[0]
    taskdict["tool"] = utils.get(tool, taskloc)[0]

    # Case 1: User supplies directory of invocations
    if op.isdir(invocation):
        invocations = os.listdir(invocation)
        taskdicts = []
        for invoc in invocations:
            tempdict = deepcopy(taskdict)
            tempinvo = utils.get(op.join(invocation, invoc), taskloc)
            tempdict["invocation"] = tempinvo
            taskdicts += [tempdict]

    # Case 2: User supplies a single invocation
    else:
        # Case 2a: User is running a BIDS app
        if kwargs.get('bids'):
            taskdicts, invocations = bidstasks(taskloc, taskdict)

        # Case 2b: User is quite simply just launching a single invocation
        else:
            taskdicts = [taskdict]
            invocations = [taskdict["invocation"]]

    # Store task definition files to disk
    taskdictnames = []
    for idx, taskdict in enumerate(taskdicts):
        taskfname = op.join(taskloc, "task-{}.json".format(idx))
        taskdictnames += [taskfname]
        with open(taskfname, 'w') as fhandle:
            fhandle.write(json.dumps(taskdict))

    return (taskdictnames, invocations)


def bidstasks(clowdrloc, taskdict):
    # TODO: document
    dataloc = taskdict["dataloc"][0]
    invocation = taskdict["invocation"]

    invo = json.load(open(invocation))
    participants = invo.get("participant_label")
    sessions = invo.get("session_label")

    # Case 1: User is running BIDS group-level analysis
    if invo.get("analysis_level") == "group":
        return ([taskdict], [invocation])

    # Case 2: User is running BIDS participant- or session-level analysis
    #       ... and specified neither participant(s) nor session(s)
    elif not participants and not sessions:
        return ([taskdict], [invocation])

    # Case 3: User is running BIDS participant- or session-level analysis
    #       ... and specified participant(s) but not session(s)
    elif participants and not sessions:
        taskdicts = []
        invos = []
        for part in participants:
            partstr = "sub-{}".format(part)

            tempdict = deepcopy(taskdict)
            tempdict["dataloc"] = [op.join(dataloc, partstr)]

            invo["participant_label"] = [part]

            invofname = op.join(clowdrloc, "invocation_sub-{}.json".format(part))
            with open(invofname, 'w') as fhandle:
                fhandle.write(json.dumps(invo))

            tempdict["invocation"] = invofname
            invos += [invofname]
            taskdicts += [tempdict]
        return (taskdicts, invos)

    # Case 4: User is running BIDS participant- or session-level analysis
    #       ... and specified participants(s) and session(s)
    elif participants and sessions:
        taskdicts = []
        invos = []
        for part in participants:
            partstr = "sub-{}".format(part)

            for sesh in sessions:
                seshstr = "ses-{}".format(sesh)

                tempdict = deepcopy(taskdict)
                tempdict["dataloc"] = [op.join(dataloc, partstr, seshstr)]

                invo["participant_label"] = [part]
                invo["session_label"] = [sesh]

                invofname = op.join(clowdrloc, "invocation_sub-{}_ses-{}.json".format(part, sesh))
                with open(invofname, 'w') as fhandle:
                    fhandle.write(json.dumps(invo))

                tempdict["invocation"] = invofname
                invos += [invofname]
                taskdicts += [tempdict]
        return (taskdicts, invos)

    # Case 5: User is running BIDS participant- or session-level analysis
    #       ... and specified sessions(s) but not participant(s)
    else:
        print("Error: Invalid BIDS mode not supported....")
        print("       Must specify participant label if specifying sessions!")
        sys.exit(-1)


def prepare(tasks, tmploc, clowdrloc):
    # TODO: document

    # Modify tasks
    for task in tasks:
        with open(task) as fhandle:
            task_dict = json.load(fhandle)

        task_dict["invocation"] = op.join(clowdrloc,
                                          op.relpath(task_dict["invocation"],
                                                     tmploc))
        task_dict["taskloc"] = op.join(clowdrloc,
                                       op.relpath(task_dict["taskloc"],
                                                  tmploc))
        task_dict["tool"] = op.join(clowdrloc, op.relpath(task_dict["tool"],
                                                          tmploc))

        with open(task, 'w') as fhandle:
            fhandle.write(json.dumps(task_dict))

    return 0

