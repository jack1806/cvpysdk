# -*- coding: utf-8 -*-

# --------------------------------------------------------------------------
# Copyright Commvault Systems, Inc.
# See LICENSE.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""File for operating on a Postgres Server Subclient

PostgresSubclient is the only class defined in this file.

PostgresSubclient: Derived class from Subclient Base class, representing a HANA server subclient,
                        and to perform operations on that subclient

PostgresSubclient:
==================

    _backup_request_json()               --  prepares the json for the backup request

    _get_subclient_properties()          --  gets the subclient related properties of
    PostgreSQL subclient

    _get_subclient_properties_json()     --  gets all the subclient related properties of
    PostgreSQL subclient

    backup()                             --  Runs a backup job for the subclient of the
    level specified

    restore_postgres_server()            --  Method to restore the Postgres server



PostgresSubclient instance Attributes
=====================================

    **content**                          --  returns list of databases which are part
    of subclient content

"""
from __future__ import unicode_literals
from .dbsubclient import DatabaseSubclient
from ..exception import SDKException


class PostgresSubclient(DatabaseSubclient):
    """Derived class from Subclient Base class, representing a file system subclient,
        and to perform operations on that subclient."""

    def __init__(self, backupset_object, subclient_name, subclient_id=None):
        """
        Constructor for the class

        Args:
            backupset_object  (object)  -- instance of the Backupset class

            subclient_name    (str)     -- name of the subclient

            subclient_id      (str)     -- id of the subclient

        """
        super(PostgresSubclient, self).__init__(
            backupset_object, subclient_name, subclient_id)
        self._postgres_properties = {}
        self._postgres_browse_options = None
        self._postgres_destination = None
        self._postgres_file_options = None
        self._postgres_restore_options = None

    @property
    def content(self):
        """returns list of databases which are part of subclient content"""
        self._content = None
        if not self.is_default_subclient:
            if 'content' in self._subclient_properties:
                self._content = self._subclient_properties['content']
        if not self._content is None:
            database_list = list()
            for database in self._content:
                if database.get('postgreSQLContent'):
                    if database['postgreSQLContent'].get('databaseName'):
                        database_list.append(database[
                            'postgreSQLContent']['databaseName'].lstrip("/"))
            return database_list

    def _backup_request_json(
            self,
            backup_level,
            backup_prefix=None):
        """
        prepares the json for the backup request

            Args:
                backup_level   (list)  --  level of backup the user wish to run
                        Full / Incremental / Differential

                backup_prefix   (str)   --  the prefix that the user wish to add to the backup

            Returns:
                dict - JSON request to pass to the API

        """
        request_json = self._backup_json(backup_level, False, "BEFORE_SYNTH")
        hana_options = {
            "hanaOptions": {
                "backupPrefix": str(backup_prefix)
            }
        }
        request_json["taskInfo"]["subTasks"][0]["options"]["backupOpts"].update(
            hana_options
        )

        return request_json

    def _get_subclient_properties(self):
        """gets the subclient related properties of PostgreSQL subclient.

        """
        super(PostgresSubclient, self)._get_subclient_properties()
        if 'postgreSQLSubclientProp' not in self._subclient_properties:
            self._subclient_properties['postgreSQLSubclientProp'] = {}
        self._postgres_properties = self._subclient_properties['postgreSQLSubclientProp']

    def _get_subclient_properties_json(self):
        """gets all the subclient related properties of PostgreSQL subclient.

           Returns:
                dict - all subclient properties put inside a dict

        """
        subclient_json = {
            "subClientProperties":
                {
                    "postgreSQLSubclientProp": self._postgres_properties,
                    "impersonateUser": self._impersonateUser,
                    "proxyClient": self._proxyClient,
                    "subClientEntity": self._subClientEntity,
                    "content": self._content,
                    "commonProperties": self._commonProperties,
                    "contentOperationType": 1
                }
        }
        return subclient_json

    def backup(
            self,
            backup_level="Differential",
            backup_prefix=None):
        """Runs a backup job for the subclient of the level specified.

            Args:
                backup_level        (str)   --  level of backup the user wish to run
                        Full / Incremental / Differential

                    default: Differential

                backup_prefix       (str)   --  the prefix that the user wish to add to the backup
                    default: None

            Returns:
                object - instance of the Job class for this backup job

            Raises:
                SDKException:
                    if backup level specified is not correct

                    if response is empty

                    if response is not success

        """
        backup_level = backup_level.lower()

        if backup_level not in ['full', 'incremental', 'differential']:
            raise SDKException('Subclient', '103')

        if backup_prefix is None:
            return super(PostgresSubclient, self).backup(backup_level)
        request_json = self._backup_request_json(
            backup_level, backup_prefix)
        flag, response = self._commcell_object._cvpysdk_object.make_request(
            'POST', self._commcell_object._services['CREATE_TASK'], request_json
        )
        return self._process_backup_response(flag, response)

    def restore_postgres_server(
            self,
            database_list=None,
            dest_client_name=None,
            dest_instance_name=None,
            copy_precedence=None,
            from_time=None,
            to_time=None,
            clone_env=False,
            clone_options=None):
        """
        Method to restore the Postgres server

            Args:

                database_list               (List) -- List of databases

                dest_client_name            (str)  -- Destination Client name

                dest_instance_name          (str)  -- Destination Instance name

                copy_precedence             (int)  -- Copy precedence associted with storage

                from_time               (str)   --  time to retore the contents after
                    format: YYYY-MM-DD HH:MM:SS

                    default: None

                to_time                 (str)   --  time to retore the contents before
                    format: YYYY-MM-DD HH:MM:SS

                    default: None

                clone_env                   (bool)  --  boolean to specify whether the database
                should be cloned or not

                    default: False

                clone_options               (dict)  --  clone restore options passed in a dict

                    default: None

                    Accepted format: {
                                        "stagingLocaion": "/gk_snap",
                                        "forceCleanup": True,
                                        "port": "5595",
                                        "libDirectory": "/opt/PostgreSQL/9.6/lib",
                                        "isInstanceSelected": True,
                                        "reservationPeriodS": 3600,
                                        "user": "postgres",
                                        "binaryDirectory": "/opt/PostgreSQL/9.6/bin"
                                     }

            Returns:
                object -- Job containing restore details

        """
        backup_set_object = self._backupset_object
        instance_object = backup_set_object._instance_object
        if dest_client_name is None:
            dest_client_name = instance_object._agent_object._client_object.client_name

        if dest_instance_name is None:
            dest_instance_name = instance_object.instance_name

        backupset_name = backup_set_object.backupset_name

        if backupset_name.lower() == "fsbasedbackupset":
            backupset_flag = True
            database_list = ["/data"]
        else:
            backupset_flag = False

        instance_object._restore_association = self._subClientEntity
        return instance_object.restore_in_place(
            database_list,
            dest_client_name,
            dest_instance_name,
            backupset_name,
            backupset_flag,
            copy_precedence=copy_precedence,
            from_time=from_time,
            to_time=to_time,
            clone_env=clone_env,
            clone_options=clone_options)
