# ~/benchmaster/tests/integration_test_suite.py

import unittest
import os
import datetime
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, Machine, BenchmarkJob, Result, Alert, Threshold, get_engine, init_db
from parsers.cinebench import CinebenchParser
from parsers.crystaldiskmark import CrystalDiskMarkParser
from parsers.threedmark import ThreeDMarkParser
from parsers.aida64 import AIDA64Parser
from agent.fleet_manager import FleetManager
import agent.fleet_manager as fm

# --- Test Configuration ---
TEST_DB_URL = "sqlite:///~/benchmaster/db/benchmaster_test.db"

class BenchMasterIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = get_engine(TEST_DB_URL)
        init_db(cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine)
        cls.fleet_manager = FleetManager(db_url=TEST_DB_URL)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)

    def setUp(self):
        self.session = self.SessionLocal()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    # --- Category 1: API & DB Integrity ---

    def test_tc_api_01_machine_registration(self):
        new_machine = Machine(hostname="test-node-01", ip="192.168.1.10", cpu="Intel i9", ram=64)
        self.session.add(new_machine)
        self.session.commit()
        db_machine = self.session.query(Machine).filter_by(hostname="test-node-01").first()
        self.assertIsNotNone(db_machine)
        self.assertEqual(db_machine.ip, "192.168.1.10")

    def test_tc_api_02_job_lifecycle(self):
        machine = Machine(hostname="job-node", ip="1.1.1.1")
        self.session.add(machine)
        self.session.commit()
        job = BenchmarkJob(machine_id=machine.id, benchmark="cinebench", status="PENDING")
        self.session.add(job)
        self.session.commit()
        job.status = "RUNNING"
        job.started_at = datetime.datetime.utcnow()
        self.session.commit()
        db_job = self.session.query(BenchmarkJob).filter_by(id=job.id).first()
        self.assertEqual(db_job.status, "RUNNING")

    def test_tc_api_03_threshold_crud(self):
        t = Threshold(benchmark="cinebench", metric_key="single_core", min_val=1000.0, max_val=2000.0, version="1.0")
        self.session.add(t)
        self.session.commit()
        t.max_val = 2500.0
        self.session.commit()
        db_t = self.session.query(Threshold).filter_by(benchmark="cinebench").first()
        self.assertEqual(db_t.max_val, 2500.0)
        self.session.delete(db_t)
        self.session.commit()
        self.assertIsNone(self.session.query(Threshold).filter_by(benchmark="cinebench").first())

    # --- Category 2: Parser Robustness ---

    def test_tc_par_01_cinebench(self):
        parser = CinebenchParser()
        log = "Cinebench R23\nSingle Core Score: 1200.5\nMulti Core Score: 15000.2"
        res = parser.parse(log)
        self.assertEqual(res["single_core"], 1200.5)
        self.assertEqual(res["multi_core"], 15000.2)

    def test_tc_par_02_cdm(self):
        parser = CrystalDiskMarkParser()
        log = "Sequential Read: 500.0 MB/s\nSequential Write: 400.0 MB/s\nRandom 4K Read: 40.0 MB/s\nRandom 4K Write: 80.0 MB/s"
        res = parser.parse(log)
        self.assertEqual(res["seq_read"], 500.0)
        self.assertEqual(res["rand_4k_read"], 40.0)

    def test_tc_par_05_malformed_log(self):
        parser = CinebenchParser()
        res = parser.parse("corrupted data... no scores here")
        self.assertEqual(res, {})

    # --- Category 3: Agent & Monitoring ---

    def test_tc_agt_01_offline_detection(self):
        old_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=15)
        machine = Machine(hostname="offline-node", ip="10.0.0.1", last_heartbeat=old_time)
        self.session.add(machine)
        self.session.commit()
        self.fleet_manager.check_machine_health(self.session)
        self.session.commit()
        alert = self.session.query(Alert).filter_by(machine_id=machine.id, alert_type="OFFLINE").first()
        self.assertIsNotNone(alert)

    def test_tc_agt_02_anomaly_detection(self):
        """TC-AGT-02: Simulate score anomaly detection."""
        machine = Machine(hostname="anomaly-node", ip="10.0.0.2")
        self.session.add(machine)
        self.session.commit()

        # 1. Create a job first to ensure ALL results have a valid job_id
        job = BenchmarkJob(machine_id=machine.id, benchmark="cinebench", status="COMPLETED")
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        self.assertIsNotNone(job.id)

        # 2. Inject historical data using the valid job_id
        for i in range(5):
            res = Result(
                job_id=job.id,
                machine_id=machine.id,
                benchmark="cinebench",
                scores_json={"single_core": 1000.0},
                system_snapshot_json={},
                timestamp=datetime.datetime.utcnow() - datetime.timedelta(days=i+1)
            )
            self.session.add(res)
        self.session.commit()

        # 3. Inject anomaly using the same valid job_id
        anomaly_res = Result(
            job_id=job.id,
            machine_id=machine.id,
            benchmark="cinebench",
            scores_json={"single_core": 500.0},
            system_snapshot_json={},
            timestamp=datetime.datetime.utcnow()
        )
        self.session.add(anomaly_res)
        self.session.commit()

        # 4. Run detection
        self.fleet_manager.check_score_anomalies(self.session)
        self.session.commit()

        # 5. Verify alert
        alert = self.session.query(Alert).filter_by(machine_id=machine.id, alert_type="LOW_SCORE").first()
        self.assertIsNotNone(alert)

    # --- Category 4: End-to-End Workflow ---

    @patch('agent.fleet_manager.requests.post')
    def test_tc_e2e_02_telegram_notification(self, mock_post):
        mock_post.return_value.status_code = 200
        with patch.object(fm, 'TELEGRAM_BOT_TOKEN', 'fake_token'), \
             patch.object(fm, 'TELEGRAM_CHAT_ID', 'fake_chat_id'):
            self.fleet_manager._send_telegram_message("Test message")
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            self.assertIn("fake_token", args[0])
            self.assertEqual(kwargs['json']['text'], "Test message")

if __name__ == "__main__":
    unittest.main()
