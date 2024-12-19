import logging
import os
import xml
from xml.etree import ElementTree

from app.runners.processors.abstract_processor import AbstractProcessor

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class SonarQubeProcessor(AbstractProcessor):
    def process(self, path: str):
        filepath = f"{path}/sonar-project.properties"
        sonarqube_project_key = None
        path_pom = f"{path}/pom.xml"
        if os.path.exists(filepath):
            from jproperties import Properties

            configs = Properties()
            with open(filepath, "rb") as config_file:
                configs.load(config_file)
            _key = configs.get("sonar.projectKey")
            if _key is not None:
                sonarqube_project_key = _key.data

        if sonarqube_project_key is None and os.path.exists(path_pom):
            try:
                artifact_id = None
                namespaces = {"xmlns": "http://maven.apache.org/POM/4.0.0"}
                tree = ElementTree.parse(path_pom)
                root = tree.getroot()
                _artifact_id = root.find("xmlns:artifactId", namespaces=namespaces)
                if _artifact_id is not None:
                    artifact_id = _artifact_id.text
                group_id_node = root.find("xmlns:groupId", namespaces=namespaces)
                group_id = None
                if group_id_node is None:
                    _group_id_node = root.find("xmlns:parent", namespaces=namespaces)
                    if _group_id_node is not None:
                        group_id_node = _group_id_node.find(
                            "xmlns:groupId", namespaces=namespaces
                        )
                    if group_id_node is not None:
                        group_id = group_id_node.text
                else:
                    group_id = group_id_node.text
                if group_id is not None and artifact_id is not None:
                    sonarqube_project_key = f"{group_id}:{artifact_id}"
            except xml.etree.ElementTree.ParseError as e:
                log.warning(e)
        self.repo.sonarqube_project_key = sonarqube_project_key
        self.session.commit()
