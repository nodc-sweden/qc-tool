from qc_tool.models.visits_model import VisitsModel


class FeedbackService:
    def __init__(
        self, validation_log: list = [dict], visits_model: VisitsModel = None, data=None
    ):
        self.validation_log = validation_log
        self._visits_model = visits_model
        self.data = data

        self._row_to_logs = self._index_logs_by_row()

    def _index_logs_by_row(self):
        index = {}

        for log in self.validation_log:
            if log["row_numbers"] is not None:
                for row in log["row_numbers"]:
                    index.setdefault(row, []).append(log)

        return index

    def get_visit_feedback(self):
        result = []

        for visit in self.visits:
            logs = self._get_logs_for_visit(visit)
            # TODO:
            # qc_flags = self.file_model.get_quality_flags(visit)

            result.append(
                {
                    "visit_key": visit.visit_key,
                    "errors": self._count(logs, "error"),
                    "warnings": self._count(logs, "warning"),
                    # "qc_flags": qc_flags
                }
            )

        return result

    def get_visit_details(self, visit_key):
        visit = self.visit_model.get_visit(visit_key)

        logs = self._get_logs_for_visit(visit)
        # TODO:
        # qc_flags = self.file_model.get_quality_flags(visit)

        return {
            "visit": visit,
            "logs": logs,
            # "qc_flags": qc_flags
        }

    def get_export_data(self):
        feedback = self.get_visit_feedback()

        # convert to dataframe or flat structure
        return feedback

    def _get_logs_for_visit(self, visit):
        visit_rows = set(visit.row_numbers)

        return [
            log
            for log in self.validation_log
            if visit_rows.intersection(log["row_numbers"])
        ]

    def get_logs_for_visit(self, visit):
        logs = []

        for row in visit.row_numbers:
            logs.extend(self._row_to_logs.get(row, []))

        # remove duplicates
        unique_logs = {id(log): log for log in logs}

        return list(unique_logs.values())

    def _count(self, logs, level):
        return sum(1 for log in logs if log["level"] == level)

    @property
    def log_messages(self):
        return self._log_messages
