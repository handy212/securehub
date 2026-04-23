"""
Drop orphaned cctv_videochannel and cctv_videodevice tables left behind
when the cctv app was removed from INSTALLED_APPS without a cleanup migration.

cctv_videodevice had a DEFERRABLE FK to sites_site, which caused a
"FOREIGN KEY constraint failed" at commit time whenever a Site was deleted
via the Django admin (the ORM collector doesn't know about unregistered tables).
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0013_site_primary_industry_site_secondary_industry_and_more'),
    ]

    operations = [
        # Drop child table first to satisfy FK ordering.
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS "cctv_videochannel";',
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS "cctv_videodevice";',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
