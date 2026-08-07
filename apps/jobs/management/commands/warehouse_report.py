import duckdb
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.db.models.functions import TruncDate

from apps.jobs.models import JobEvent
from apps.jobs.warehouse import warehouse_path

REPORT_SQL = [
    ("Top sources by job count", """
        SELECT source_name, count(*) AS n
        FROM fact_jobs JOIN dim_source USING (source_key)
        GROUP BY source_name ORDER BY n DESC LIMIT 10
    """),
    ("Monthly job volume", """
        SELECT year, month, count(*) AS n
        FROM fact_jobs JOIN dim_date USING (date_key)
        GROUP BY year, month ORDER BY year, month
    """),
    ("Salary distribution by work type", """
        SELECT work_type, count(*) AS n, round(avg(salary)) AS avg_salary
        FROM fact_jobs JOIN dim_location USING (location_key)
        WHERE salary > 0 GROUP BY work_type ORDER BY n DESC
    """),
    ("Top companies", """
        SELECT company, count(*) AS n
        FROM fact_jobs JOIN dim_company USING (company_key)
        GROUP BY company ORDER BY n DESC LIMIT 10
    """),
    ("Fetch runs by source", """
        SELECT source, sum(job_count) AS jobs, count(*) AS runs
        FROM fact_fetch_runs GROUP BY source ORDER BY jobs DESC
    """),
]


class Command(BaseCommand):
    help = "Print preset analytics from the local DuckDB warehouse"

    def handle(self, *args, **options):
        path = warehouse_path()
        if not path.exists():
            raise CommandError(
                "Warehouse not built yet. Run 'manage.py build_warehouse' first."
            )

        con = duckdb.connect(str(path))
        try:
            for title, sql in REPORT_SQL:
                self.stdout.write(f"\n== {title} ==")
                rows = con.execute(sql).fetchall()
                if not rows:
                    self.stdout.write("  (no data)")
                    continue
                for row in rows:
                    self.stdout.write("  " + " | ".join(str(v) for v in row))
        finally:
            con.close()

        trend = (
            JobEvent.objects.filter(event_type="matched")
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(n=Count("id"))
            .order_by("-day")[:10]
        )
        self.stdout.write("\n== Matched jobs per day (live) ==")
        if not trend:
            self.stdout.write("  (no data)")
        for row in trend:
            self.stdout.write(f"  {row['day']}: {row['n']}")
