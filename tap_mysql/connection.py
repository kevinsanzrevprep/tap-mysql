#!/usr/bin/env python3

import backoff

import pymysql
from pymysql.constants import CLIENT

import singer
import ssl

LOGGER = singer.get_logger()

CONNECT_TIMEOUT_SECONDS = 300
READ_TIMEOUT_SECONDS = 3600

# We need to hold onto this for self-signed SSL
match_hostname = ssl.match_hostname

@backoff.on_exception(backoff.expo,
                      (pymysql.err.OperationalError),
                      max_tries=5,
                      factor=2)
def connect_with_backoff(connection):
    connection.connect()


def parse_internal_hostname(hostname):
    # special handling for google cloud
    if ":" in hostname:
        parts = hostname.split(":")
        if len(parts) == 3:
            return parts[0] + ":" + parts[2]
        return parts[0] + ":" + parts[1]

    return hostname


class MySQLConnection(pymysql.connections.Connection):
    def __init__(self, config):
        # Google Cloud's SSL involves a self-signed certificate. This certificate's
        # hostname matches the form {instance}:{box}. The hostname displayed in the
        # Google Cloud UI is of the form {instance}:{region}:{box} which
        # necessitates the "parse_internal_hostname" function to get the correct
        # hostname to match.
        # The "internal_hostname" config variable allows for matching the SSL
        # against a host that doesn't match the host we are connecting to. In the
        # case of Google Cloud, we will be connecting to an IP, not the hostname
        # the SSL certificate expects.
        # The "ssl.match_hostname" function is patched to check against the
        # internal hostname rather than the host of the connection. In the event
        # that the connection fails, the patch is reverted by reassigning the
        # patched out method to it's original spot.

        args = {
            "user": config["user"],
            "password": config["password"],
            "host": config["host"],
            "port": int(config["port"]),
            "cursorclass": config.get("cursorclass") or pymysql.cursors.SSCursor,
            "connect_timeout": CONNECT_TIMEOUT_SECONDS,
            "read_timeout": READ_TIMEOUT_SECONDS,
            "charset": "utf8",
        }

        ssl_arg = None

        if config.get("database"):
            args["database"] = config["database"]

        # Attempt self-signed SSL if config vars are present
        if config.get("ssl_ca") and config.get("ssl_cert") and config.get("ssl_key"):
            LOGGER.info("Using custom certificate authority")

            # The SSL module requires files not data, so we have to write out the
            # data to files. After testing with `tempfile.NamedTemporaryFile`
            # objects, I kept getting "File name too long" errors as the temp file
            # names were > 99 chars long in some cases. Since the box is ephemeral,
            # we don't need to worry about cleaning them up.
            with open("ca.pem", "wb") as ca_file:
                ca_file.write(config["ssl_ca"].encode('utf-8'))

            with open("cert.pem", "wb") as cert_file:
                cert_file.write(config["ssl_cert"].encode('utf-8'))

            with open("key.pem", "wb") as key_file:
                key_file.write(config["ssl_key"].encode('utf-8'))

            ssl_arg = {
                "ca": "./ca.pem",
                "cert": "./cert.pem",
                "key": "./key.pem",
            }

            # override match hostname for google cloud
            if config.get("internal_hostname"):
                parsed_hostname = parse_internal_hostname(config["internal_hostname"])
                ssl.match_hostname = lambda cert, hostname: match_hostname(cert, parsed_hostname)

        super().__init__(defer_connect=True, ssl=ssl_arg, **args)

        # Attempt SSL
        if config.get("ssl") == 'true':
            LOGGER.info("Attempting SSL connection")
            self.ssl = True
            self.ctx = ssl.create_default_context()
            self.ctx.check_hostname = False
            self.ctx.verify_mode = ssl.CERT_NONE
            self.client_flag |= CLIENT.SSL


def make_connection_wrapper(config):
    class ConnectionWrapper(MySQLConnection):
        def __init__(self, *args, **kwargs):
            config["cursorclass"] = kwargs.get('cursorclass')
            super().__init__(config)

            connect_with_backoff(self)

    return ConnectionWrapper
