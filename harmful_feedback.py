import functions_framework
import pymysql
import sqlalchemy
import os
from flask import Request, jsonify
from google.cloud.sql.connector import Connector, IPTypes
from datetime import datetime, timedelta

# Database connection setup
def connect_with_connector() -> sqlalchemy.engine.base.Engine:
    os.environ["INSTANCE_CONNECTION_NAME"] = 'support-assist-384720:us-central1:support-assist-v2'
    os.environ["DB_USER"] = 'swapnil@terrablue.ai'
    os.environ["DB_PASS"] = 'swapnil@terrablue.ai'
    os.environ["DB_NAME"] = 'sav2_responses'

    instance_connection_name = os.environ["INSTANCE_CONNECTION_NAME"]
    db_user = os.environ["DB_USER"]
    db_pass = os.environ["DB_PASS"]
    db_name = os.environ["DB_NAME"]

    ip_type = IPTypes.PRIVATE if os.environ.get("PRIVATE_IP") else IPTypes.PUBLIC
    connector = Connector(ip_type)

    def getconn():
        return connector.connect(
            instance_connection_name,
            "pymysql",
            user=db_user,
            password=db_pass,
            db=db_name
        )

    pool = sqlalchemy.create_engine(
        "mysql+pymysql://",
        creator=getconn,
    )
    return pool

# Function to fetch the next harmful feedback row
def get_next_harmful_feedback():
    pool = connect_with_connector()
    with pool.connect() as conn:
        row = conn.execute(
            sqlalchemy.text(
                """
                SELECT id, cid, product, question, response, helpfulness, comments, time_stamp
                FROM `sav2_responses`.`Feedback_Collection`
                WHERE helpfulness = 'Harmful'
                AND audit_category IS NULL
                AND LENGTH(TRIM(skip_reason)) = 0
                ORDER BY time_stamp ASC
                LIMIT 1;
                """
            )
        ).fetchone()
        
        if row:
            return dict(row._mapping)
        else:
            return None

# Cloud Function handler
@functions_framework.http
def fetch_next_feedback(request: Request):
    try:
        data = get_next_harmful_feedback()
        if data:
            return jsonify({"status": "success", "data": data}), 200
        else:
            return jsonify({"status": "no_data"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
