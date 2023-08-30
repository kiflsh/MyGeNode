#########################################################################
#
# Copyright (C) 2023 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

import re
import logging
import traceback

from django.conf import settings
from django.utils.module_loading import import_string

from geonode.base.models import Region
from django.contrib.gis.geos import GEOSGeometry

logger = logging.getLogger(__name__)


def assign_regions(instance, *args, **kwargs):
    region_handler = getattr(settings, "DEFAULT_REGION_HANDLER", None)
    if region_handler:
        handler = import_string(region_handler)(instance)
        instance = handler.assign_regions(*args, **kwargs)
    return instance


class BaseRegionAssignor(object):
    def __init__(self, instance) -> None:
        self.instance = instance

    def assign_regions(self, *args, **kwargs):
        return self.instance


class SpatialPredicateRegionAssignor(BaseRegionAssignor):
    def assign_regions(self, *args, **kwargs):
        if not self.instance.regions or self.instance.regions.count() == 0:
            poly1 = self._get_poly_from_instance()

            queryset = Region.objects.all().order_by("name")
            global_regions = []
            regions_to_add = []
            for region in queryset:
                try:
                    if region.is_assignable_to_geom(poly1):
                        regions_to_add.append(region)
                    if region.level == 0 and region.parent is None:
                        global_regions.append(region)
                except Exception:
                    tb = traceback.format_exc()
                    if tb:
                        logger.debug(tb)
            if regions_to_add or global_regions:
                if regions_to_add:
                    self.instance.regions.add(*regions_to_add)
                else:
                    self.instance.regions.add(*global_regions)
        return self.instance

    def _get_poly_from_instance(self):
        srid1, wkt1 = self.instance.geographic_bounding_box.split(";")
        srid1 = re.findall(r"\d+", srid1)
        poly1 = GEOSGeometry(wkt1, srid=int(srid1[0]))
        poly1.transform(4326)
        return poly1
