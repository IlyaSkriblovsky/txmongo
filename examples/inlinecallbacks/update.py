#!/usr/bin/env python
# coding: utf-8
# Copyright 2009-2014 The txmongo authors.  All rights reserved.
# Use of this source code is governed by the Apache License that can be
# found in the LICENSE file.

import _local_path
from twisted.internet import defer, reactor

import txmongo


@defer.inlineCallbacks
def example():
    mongo = yield txmongo.MongoConnection()

    foo = mongo.foo  # `foo` database
    test = foo.test  # `test` collection

    # insert
    yield test.insert_one({"foo": "bar", "name": "bla"})

    # update
    result = yield test.update_one({"foo": "bar"}, {"$set": {"name": "john doe"}})
    print("result:", result)


if __name__ == "__main__":
    example().addCallback(lambda ign: reactor.stop())
    reactor.run()
