#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""Execute statements against Amazon Redshift, using redshift_connector."""
try:
    from functools import cached_property
except ImportError:
    from cached_property import cached_property
from typing import Dict, Union

import redshift_connector
from redshift_connector import Connection as RedshiftConnection

from airflow.hooks.dbapi import DbApiHook


class RedshiftStatementHook(DbApiHook):
    """
    Execute statements against Amazon Redshift, using redshift_connector

    This hook requires the redshift_conn_id connection. This connection must
    be initialized with the host, port, login, password. Additional connection
    options can be passed to extra as a JSON string.

    :param redshift_conn_id: reference to
        :ref:`Amazon Redshift connection id<howto/connection:redshift>`
    :type redshift_conn_id: str

    .. note::
        get_sqlalchemy_engine() and get_uri() depend on sqlalchemy-amazon-redshift
    """

    conn_name_attr = 'redshift_conn_id'
    default_conn_name = 'redshift_default'
    conn_type = 'redshift+redshift_connector'
    hook_name = 'Amazon Redshift'
    supports_autocommit = True

    @staticmethod
    def get_ui_field_behavior() -> Dict:
        """Returns custom field behavior"""
        return {
            "hidden_fields": [],
            "relabeling": {'login': 'User', 'schema': 'Database'},
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    @cached_property
    def conn(self):
        return self.get_connection(
            self.redshift_conn_id  # type: ignore[attr-defined]  # pylint: disable=no-member
        )

    def _get_conn_params(self) -> Dict[str, Union[str, int]]:
        """Helper method to retrieve connection args"""
        conn = self.conn

        conn_params: Dict[str, Union[str, int]] = {}

        if conn.login:
            conn_params['user'] = conn.login
        if conn.password:
            conn_params['password'] = conn.password
        if conn.host:
            conn_params['host'] = conn.host
        if conn.port:
            conn_params['port'] = conn.port
        if conn.schema:
            conn_params['database'] = conn.schema

        return conn_params

    def get_uri(self) -> str:
        """
        Override DbApiHook get_uri method for get_sqlalchemy_engine()

        .. note::
            Value passed to connection extra parameter will be excluded
            from returned uri but passed to get_sqlalchemy_engine()
            by default
        """
        from sqlalchemy.engine.url import URL

        conn_params = self._get_conn_params()

        conn = self.conn

        conn_type = conn.conn_type or RedshiftStatementHook.conn_type

        if 'user' in conn_params:
            conn_params['username'] = conn_params.pop('user')

        return URL(drivername=conn_type, **conn_params).__str__()

    def get_sqlalchemy_engine(self, engine_kwargs=None):
        """Overrides DbApiHook get_sqlalchemy_engine to pass redshift_connector specific kwargs"""
        conn_kwargs = self.conn.extra_dejson
        if engine_kwargs is None:
            engine_kwargs = {}

        if "connect_args" in engine_kwargs:
            engine_kwargs["connect_args"] = {**conn_kwargs, **engine_kwargs["connect_args"]}
        else:
            engine_kwargs["connect_args"] = conn_kwargs

        return super().get_sqlalchemy_engine(engine_kwargs=engine_kwargs)

    def get_conn(self) -> RedshiftConnection:
        """Returns a redshift_connector.Connection object"""
        conn_params = self._get_conn_params()
        conn_kwargs = self.conn.extra_dejson
        conn_kwargs: Dict = {**conn_params, **conn_kwargs}
        conn: RedshiftConnection = redshift_connector.connect(**conn_kwargs)

        return conn
