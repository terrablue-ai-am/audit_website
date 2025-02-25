import functions_framework
import pymysql
import sqlalchemy
import os
from flask import jsonify
from google.cloud.sql.connector import Connector, IPTypes

# Database connection setup
def connect_with_connector() -> sqlalchemy.engine.base.Engine:
    os.environ["INSTANCE_CONNECTION_NAME"] = 'support-assist-384720:us-central1:support-assist-v2'
    os.environ["DB_USER"] = 'swapnil@terrablue.ai'
    os.environ["DB_PASS"] = 'swapnil@terrablue.ai'
    os.environ["DB_NAME"] = 'sav2_responses_staging'

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

# Function to update both tables in the database
def update_feedback_in_db(feedback_data):
    pool = connect_with_connector()
    
    try:
        with pool.connect() as conn:
            # Update the Feedback_Collection table
            conn.execute(
                sqlalchemy.text(
                    """
                    UPDATE `sav2_responses_staging`.`Feedback_Collection`
                    SET audit_category = :audit_category, audit_description = :audit_description
                    WHERE id = :id
                    """
                ),
                parameters=feedback_data
            )

            # Update the generative_first_reply table
            conn.execute(
                sqlalchemy.text(
                    """
                    UPDATE `sav2_responses`.`generative_first_reply`
                    SET acategory = :audit_category, adescription = :audit_description
                    WHERE cfid = :cid
                    """
                ),
                parameters=feedback_data
            )

            conn.commit()
            return True
    except Exception as e:
        print(f"Error updating feedback: {e}")
        return False

# Cloud Function handler
@functions_framework.http
def submit_feedback(request):
    try:
        request_json = request.get_json()
        if not request_json:
            return jsonify({"error": "Invalid request"}), 400

        # Extract required fields
        feedback_data = {
            "id": request_json.get("id"),  # For Feedback_Collection table
            "cid": request_json.get("cid"),  # For generative_first_reply table
            "audit_category": request_json.get("audit_category"),
            "audit_description": request_json.get("audit_description")
        }

        # Validate required inputs
        if not all(feedback_data.values()):
            return jsonify({"error": "Missing required fields"}), 400

        # Update the database
        update_success = update_feedback_in_db(feedback_data)
        if not update_success:
            return jsonify({"error": "Database update failed"}), 500

        return jsonify({"status": "success", "message": "Feedback submitted successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
