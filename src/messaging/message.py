#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  messenger.py
#
#  Copyright 2018  <bruce@emxsys.com>
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.

import os
from pprint import pprint
from datetime import datetime

class Message:

    def __init__(self, db, config):
        """
        Initialize the database tables for voice messages.
        """
        self.db = db
        self.config = config

        if self.config["DEBUG"]:
            print("Initializing Message")

        # Create the message table if it does not exist
        if self.db:
            sql = """
                CREATE TABLE IF NOT EXISTS Message (
                    MessageID INTEGER PRIMARY KEY AUTOINCREMENT,
                    CallLogID INTEGER,
                    Played BOOLEAN DEFAULT 0 NOT NULL CHECK (Played IN (0,1)),
                    Filename TEXT,
                    DateTime TEXT,
                    FOREIGN KEY(CallLogID) REFERENCES CallLog(CallLogID));"""

            curs = self.db.cursor()
            curs.executescript(sql)
            curs.close()

        if self.config["DEBUG"]:
            print("Message initialized")

    def add(self, call_no, filepath):
        """
        Adds a message to the table
        """
        sql = """
            INSERT INTO Message(
                CallLogID,
                Filename,
                DateTime)
            VALUES(?,?,?)
        """
        arguments = [
            call_no,
            filepath,
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:19])
        ]
        self.db.execute(sql, arguments)
        self.db.commit()

        # Return the MessageID
        query = "SELECT last_insert_rowid()"
        curs = self.db.cursor()
        curs.execute(query)
        msg_no = curs.fetchone()[0]
        curs.close()

        self.reset_message_indicator()
        return msg_no

    def delete(self, msg_no):
        """
        Removes the message record and associated wav file.
        """
        # Get the filename to delete
        sql = "SELECT Filename FROM Message WHERE MessageID=:msg_no"
        arguments = {'msg_no': msg_no}
        curs = self.db.execute(sql, arguments)
        results = curs.fetchone()
        curs.close()

        # Now do the deletes
        success = True
        if len(results) > 0:

            # Delete the wav file
            filename = results[0]
            print("Deleting message: {}".format(filename))
            try:
                os.remove(filename)
            except OSError as error:
                pprint(error)
                print("{} cannot be removed".format(filename))
                success = False

            # Delete the row
            if success:
                sql = "DELETE FROM Message WHERE MessageID=:msg_no"
                arguments = {'msg_no': msg_no}
                self.db.execute(sql, arguments)
                self.db.commit()

                if self.config["DEBUG"]:
                    print("Message entry removed")
                    pprint(arguments)

            self.reset_message_indicator()

        return success

    def update_played(self, msg_no, played=1):
        """
        Updates the played status of the given message
        """
        try:
            sql = "UPDATE Message SET Played=:played WHERE MessageID=:msg_no"
            arguments = {'msg_no': msg_no, 'played': played}
            self.db.execute(sql, arguments)
            self.db.commit()
        except Exception as e:
            print("** Error updating message played status:")
            pprint(e)
            return False

        self.reset_message_indicator()
        return True

    def get_unplayed_count(self):
        # Get the number of unread messages
        sql = "SELECT COUNT(*) FROM Message WHERE Played = 0"
        curs = self.db.execute(sql)
        unplayed_count = curs.fetchone()[0]
        if self.config["DEBUG"]:
            print("Unplayed message count is {}".format(unplayed_count))
        return unplayed_count

    def reset_message_indicator(self):
        message_indicator = self.config["MESSAGE_INDICATOR_LED"]
        if self.get_unplayed_count() > 0:
            message_indicator.pulse()
        else:
            message_indicator.turn_off()


def test(db, config):
    """
     Unit Tests
    """

    print("*** Running Message Unit Tests ***")

    msg = Message(db, config)

    # Test data
    caller = {"NAME": "Bruce", "NMBR": "1234567890", "DATE": "1012", "TIME": "0600"}

    try:


        count = voicemail.get_unplayed_count()
        assert count == 1, "Unplayed count should be 1"

        # List the records
        query = 'select * from Message'
        curs = db.execute(query)
        print(query + " results:")
        pprint(curs.fetchall())

        voicemail.delete_message(msg_no)

    except AssertionError as e:
        print("*** Unit Test FAILED ***")
        pprint(e)
        return 1

    print("*** Unit Tests PASSED ***")
    return 0


if __name__ == '__main__':

    # Create the test db in RAM
    import sqlite3
    db = sqlite3.connect(":memory:")

    # Add the parent directory to the path so callattendant can be found
    import os
    import sys
    currentdir = os.path.dirname(os.path.realpath(__file__))
    parentdir = os.path.dirname(currentdir)
    sys.path.append(parentdir)

    # Create and tweak a default config suitable for unit testing
    from callattendant import make_config, print_config
    config = make_config()
    config['DEBUG'] = True
    print_config(config)

    # Run the tests
    sys.exit(test(db, config))
