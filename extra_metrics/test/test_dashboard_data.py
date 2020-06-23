import unittest
import os
import json


class DashboardTestCase(unittest.TestCase):
    def test_src_code_for_dashboards_on_disk_have_the_right_keys(self):
        dashboard_path = os.path.join(os.getcwd(), "extra_metrics", "dashboards")
        self.assertTrue(os.path.exists(dashboard_path))

        count = 0

        for filename in os.listdir(dashboard_path):
            if not filename.endswith("json"):
                continue
            dashboard_full_path = os.path.join(dashboard_path, filename)
            with open(dashboard_full_path, 'r') as f:
                j = json.load(f)

                self.assertIsNotNone(j)
                keys_that_must_be_there = ["annotations", "tags", "templating", "links", "title", "timepicker"]
                for k in keys_that_must_be_there:
                    self.assertIn(k, j, f"{filename} is missing a really important key")

                # at least for now; all dashboards should have a "patching" tag
                patching_tag = "patching"
                tags = j["tags"]
                self.assertIn(patching_tag, tags, f"{filename} doesn't have a dashboard tag to link them all together - tags contains: {tags}")

                # and they should link to other dashboards with patching too
                links = j["links"]
                for link_item in links:
                    self.assertIn("tags", link_item, f"{filename} lacks the tags attribute, links wont work!")
                    self.assertIn("type", link_item)
                    self.assertEqual("dashboards", link_item["type"], f"{filename} dashboard links will be broken, the type is incorrect")
                    self.assertIn(patching_tag, link_item["tags"])

                # one of templating/list needs to be
                '''
                {
                    "current": {
                    "value": "${VAR_SERVER}",
                    "text": "${VAR_SERVER}"
                    },
                    "hide": 2,
                    "label": "Server",
                    "name": "server",
                    "options": [
                    {
                        "selected": true,
                        "value": "${VAR_SERVER}",
                        "text": "${VAR_SERVER}"
                    }
                    ],
                    "query": "${VAR_SERVER}",
                    "skipUrlSync": false,
                    "type": "constant"
                }
                '''
                found_template = False
                templating = j["templating"]
                for t_item in templating["list"]:
                    # gotta find type: constant, looking for a 'server' variable.
                    if t_item["type"] == "constant" and t_item["name"] == "server":
                        self.assertEqual(2, t_item["hide"], f"{filename} hide param has the wrong value")
                        self.assertEqual("${VAR_SERVER}", t_item["query"], f"{filename} query param has the wrong value")
                        self.assertEqual("${VAR_SERVER}", t_item["current"]["value"], f"{filename} current/value param has the wrong value")
                        self.assertEqual("${VAR_SERVER}", t_item["current"]["text"], f"{filename} current/text param has the wrong value")
                        found_template = True

                # if this fails; the templating/list items do not contain the ever critical "server" var
                self.assertTrue(found_template, f"{filename} lacks the 'server' templating item")

                count += 1

        self.assertTrue(count > 2)
