from contextlib import contextmanager
from unittest.mock import patch

from pymongo.errors import AutoReconnect
from twisted.internet import defer
from twisted.trial import unittest

import txmongo
from txmongo import MongoProtocol


class SingleCollectionTest(unittest.TestCase):
    mongo_host = "localhost"
    mongo_port = 27017

    async def setUp(self):
        self.conn = txmongo.MongoConnection(self.mongo_host, self.mongo_port)
        self.db = self.conn.mydb
        self.coll = self.db.mycol
        # MapReduce command on MongoDB ≤4.2 requires collection to actually exist
        await self.db.create_collection("mycol")

    async def tearDown(self):
        while True:
            try:
                await self.coll.drop()
                break
            except AutoReconnect:
                pass

        await self.conn.disconnect()


@contextmanager
def patch_send_msg():
    with patch.object(
        MongoProtocol, "send_msg", side_effect=MongoProtocol.send_msg, autospec=True
    ) as mock:
        yield mock
