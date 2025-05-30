# coding: utf-8
# Copyright 2010 Tryggvi Bjorgvinsson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from twisted.internet import defer
from twisted.trial import unittest

import txmongo
from txmongo import filter as qf

mongo_host = "127.0.0.1"
mongo_port = 27017


class TestAggregate(unittest.TestCase):

    timeout = 5

    @defer.inlineCallbacks
    def setUp(self):
        self.conn = yield txmongo.MongoConnection(mongo_host, mongo_port)
        self.db = self.conn.mydb
        self.coll = self.db.mycol

    @defer.inlineCallbacks
    def test_aggregate(self):
        """Test basic aggregation functionality"""
        yield self.coll.insert_many(
            [
                {"oh": "hai", "lulz": 123},
                {"oh": "kthxbye", "lulz": 456},
                {"oh": "hai", "lulz": 789},
            ]
        )

        res = yield self.coll.aggregate(
            [
                {"$project": {"oh": 1, "lolz": "$lulz"}},
                {"$group": {"_id": "$oh", "many_lolz": {"$sum": "$lolz"}}},
                {"$sort": {"_id": 1}},
            ]
        )

        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]["_id"], "hai")
        self.assertEqual(res[0]["many_lolz"], 912)
        self.assertEqual(res[1]["_id"], "kthxbye")
        self.assertEqual(res[1]["many_lolz"], 456)

        res = yield self.coll.aggregate([{"$match": {"oh": "hai"}}], full_response=True)

        self.assertIn("ok", res)
        self.assertIn("result", res)
        self.assertEqual(len(res["result"]), 2)

        res = yield self.coll.aggregate(
            [{"$match": {"oh": "hai"}}], full_response=True, initial_batch_size=1
        )

        self.assertIn("ok", res)
        self.assertIn("result", res)
        self.assertEqual(len(res["result"]), 2)

    @defer.inlineCallbacks
    def test_large_batch(self):
        """Test aggregation with a large number of objects"""
        cnt = 10000
        yield self.coll.insert_many(
            [{"key": "v{}".format(i), "value": i} for i in range(cnt)]
        )
        group = {"$group": {"_id": "$key"}}

        # Default initial batch size (determined by the database)
        res = yield self.coll.aggregate([group])
        self.assertEqual(len(res), cnt)

        # Initial batch size of zero (returns quickly in case of an error)
        res = yield self.coll.aggregate([group], initial_batch_size=0)
        self.assertEqual(len(res), cnt)

        # Small initial batch size
        res = yield self.coll.aggregate([group], initial_batch_size=10)
        self.assertEqual(len(res), cnt)

        # Initial batch size larger than the number of records
        res = yield self.coll.aggregate([group], initial_batch_size=(cnt + 10))
        self.assertEqual(len(res), cnt)

    @defer.inlineCallbacks
    def test_large_value(self):
        """Test aggregation with large objects"""
        cnt = 2
        yield self.coll.insert_many([{"x": str(i) * 1024 * 1024} for i in range(cnt)])

        group = {"$group": {"_id": "$x"}}

        # Default initial batch size (determined by the database)
        res = yield self.coll.aggregate([group])
        self.assertEqual(len(res), cnt)

        # Initial batch size of zero (returns quickly in case of an error)
        res = yield self.coll.aggregate([group], initial_batch_size=0)
        self.assertEqual(len(res), cnt)

        # Small initial batch size
        res = yield self.coll.aggregate([group], initial_batch_size=10)
        self.assertEqual(len(res), cnt)

        # Initial batch size larger than the number of records
        res = yield self.coll.aggregate([group], initial_batch_size=(cnt + 10))
        self.assertEqual(len(res), cnt)

    @defer.inlineCallbacks
    def test_comment(self):
        yield self.db.command("profile", 2)
        try:
            yield self.coll.aggregate([{"$match": {"oh": "hai"}}], comment="Hey")
            cnt = yield self.db.system.profile.count_documents(
                {"command.comment": "Hey"}
            )
            self.assertEqual(cnt, 1)
        finally:
            yield self.db.command("profile", 0)
            yield self.db.system.profile.drop()

    @defer.inlineCallbacks
    def test_max_time_ms(self):
        yield self.db.command("profile", 2)
        try:
            yield self.coll.aggregate([{"$match": {"oh": "hai"}}], max_time_ms=1234)
            cnt = yield self.db.system.profile.count_documents(
                {"command.maxTimeMS": 1234}
            )
            self.assertEqual(cnt, 1)
        finally:
            yield self.db.command("profile", 0)
            yield self.db.system.profile.drop()

    @defer.inlineCallbacks
    def test_hint(self):
        yield self.db.command("profile", 2)
        try:
            yield self.coll.create_index(qf.sort(qf.DESCENDING("x")))
            yield self.coll.aggregate(
                [{"$match": {"oh": "hai"}}], hint=qf.hint(qf.DESCENDING("x"))
            )
            cnt = yield self.db.system.profile.count_documents(
                {"command.hint": {"x": -1}}
            )
            self.assertEqual(cnt, 1)
        finally:
            yield self.db.command("profile", 0)
            yield self.db.system.profile.drop()

    def test_typechecks(self):
        self.assertRaises(TypeError, self.coll.aggregate, "invalid pipeline")
        self.assertRaises(TypeError, self.coll.aggregate, [], comment=123)
        self.assertRaises(TypeError, self.coll.aggregate, [], max_time_ms="123")

    @defer.inlineCallbacks
    def tearDown(self):
        yield self.coll.drop()
        yield self.conn.disconnect()
