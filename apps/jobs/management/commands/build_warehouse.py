from django.core.management.base import BaseCommand, CommandError

from apps.jobs.warehouse import build_warehouse


class Command(BaseCommand):
    help = "Build or refresh the local DuckDB warehouse from the data lake"

    def handle(self, *args, **options):
        result = build_warehouse()
        if "error" in result:
            raise CommandError(result["error"])
        self.stdout.write(self.style.SUCCESS(f"Warehouse built: {result['db_path']}"))
        for table, count in result["counts"].items():
            self.stdout.write(f"  {table}: {count}")
