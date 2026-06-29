import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.ml_data_readiness_audit import (
    build_ml_data_readiness_audit,
    save_ml_data_readiness_audit,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class MlDataReadinessAuditTest(unittest.TestCase):
    def _write_sources(self, root: Path) -> dict[str, Path]:
        data_dir = root / "data" / "krx_expanded"
        reports = root / "data" / "reports"
        metadata = root / "data" / "krx_metadata"
        ledger = reports / "monthly_candidate_research_ledger.csv"
        quality = reports / "monthly_validation_data_quality.csv"
        exclusions = reports / "data_quality_excluded_symbols.csv"
        universe = reports / "monthly_universe_price_coverage.csv"
        fundamentals = reports / "regime_sideways_fundamental_pit_availability_audit.csv"

        dates = [
            "2024-01-31",
            "2024-02-29",
            "2024-03-29",
            "2024-04-30",
            "2024-05-31",
            "2024-06-28",
            "2024-07-31",
            "2024-08-30",
            "2024-09-30",
        ]
        for symbol, base in (("111111", 100.0), ("222222", 200.0)):
            rows = ["date,open,high,low,close,volume"]
            for index, day in enumerate(dates):
                close = base + index * (2 if symbol == "111111" else -3)
                rows.append(f"{day},{close - 1},{close + 1},{close - 2},{close},1000")
            _write(data_dir / f"{symbol}.csv", "\n".join(rows) + "\n")

        _write(
            ledger,
            "candidate_id,status,protected_from_tuning,baseline_cutoff,post_cutoff_oos_used\n"
            "proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244,PAPER_REVIEW,True,2024-08-30,existing_observation_only\n",
        )
        _write(
            quality,
            "symbol,status,first_date,last_date,rows,duplicate_dates,nonpositive_price_rows,reason\n"
            "111111,PASS,2024-01-31,2024-09-30,9,0,0,passed\n"
            "222222,PASS,2024-01-31,2024-09-30,9,0,0,passed\n",
        )
        _write(exclusions, "symbol,status,reason\n999999,BLOCK,bad price\n")
        _write(
            universe,
            "date,universe_symbols,price_symbols,covered_symbols,excluded_symbols,missing_symbols,coverage_pct,status,missing_preview,excluded_preview\n"
            "2024-01-31,2,2,2,0,0,100,PASS,,\n",
        )
        _write(metadata / "krx_universe_monthly.csv", "date,symbol\n2024-01-31,111111\n")
        _write(
            fundamentals,
            "symbol,row_status,locally_usable_by_audit_as_of\n111111,future_local_collection,False\n",
        )
        return {
            "price_dir": data_dir,
            "candidate_ledger_csv": ledger,
            "data_quality_csv": quality,
            "data_quality_exclusions_csv": exclusions,
            "universe_coverage_csv": universe,
            "pit_universe_csv": metadata / "krx_universe_monthly.csv",
            "fundamental_pit_audit_csv": fundamentals,
        }

    def test_audit_reports_cutoff_safe_baseline_ml_readiness(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_sources(Path(tmp))

            rows = build_ml_data_readiness_audit(**paths)
            by_metric = {row["metric"]: row for row in rows}

            self.assertEqual("summary", rows[0]["metric"])
            self.assertEqual("ready_for_baseline_tabular_ml", rows[0]["status"])
            self.assertEqual("baseline_tabular_ml", by_metric["recommended_model_start"]["value"])
            self.assertEqual("not_ready", by_metric["deep_learning_status"]["status"])
            self.assertEqual("False", by_metric["post_cutoff_data_used_for_train"]["value"])
            self.assertEqual("2024-08-30", by_metric["train_cutoff"]["value"])
            self.assertEqual("2", by_metric["available_symbol_count"]["value"])
            self.assertEqual("14", by_metric["monthly_label_count"]["value"])
            self.assertEqual("True", by_metric["pit_universe_available"]["value"])
            self.assertEqual("True", by_metric["data_quality_exclusion_needed"]["value"])
            self.assertEqual("False", by_metric["trading_allowed"]["value"])
            self.assertEqual("none", by_metric["production_effect"]["value"])
            self.assertIn("return_1m", by_metric["feature_candidates"]["value"])
            self.assertIn("positive=7", by_metric["label_distribution"]["value"])
            self.assertIn("negative=7", by_metric["label_distribution"]["value"])

    def test_missing_pit_universe_warns_but_keeps_no_trading_flags(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_sources(Path(tmp))
            paths["pit_universe_csv"].unlink()
            paths["universe_coverage_csv"].unlink()

            rows = build_ml_data_readiness_audit(**paths)
            by_metric = {row["metric"]: row for row in rows}

            self.assertEqual("partial_data_only", rows[0]["status"])
            self.assertEqual("False", by_metric["pit_universe_available"]["value"])
            self.assertEqual("False", by_metric["trading_allowed"]["value"])
            self.assertEqual("none", by_metric["production_effect"]["value"])

    def test_save_writes_csv_and_markdown_with_do_not_trade_notice(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._write_sources(root)
            rows = build_ml_data_readiness_audit(**paths)
            csv_output = root / "data" / "reports" / "ml_data_readiness_audit.csv"
            md_output = root / "data" / "reports" / "ml_data_readiness_audit.md"

            save_ml_data_readiness_audit(rows, csv_output, md_output)

            saved = _read_rows(csv_output)
            markdown = md_output.read_text(encoding="utf-8")
            self.assertEqual("summary", saved[0]["metric"])
            self.assertIn("Do Not Trade / Data Readiness Audit Only", markdown)
            self.assertIn("does not train models", markdown)


if __name__ == "__main__":
    unittest.main()
