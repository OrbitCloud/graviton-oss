import enum

import jinja2
import pulumi
from pulumi_cloudinit import ConfigPartArgs


class ContentType(enum.StrEnum):
    CONFIG = "text/cloud-config"
    SHELL = "text/x-shellscript"
    BOOTHOOK = "text/cloud-boothook"
    JINJA2 = "text/jinja2"
    PART_HANDLER = "text/part-handler"
    UPSTART_JOB = "text/upstart-job"
    INCLUDE_ONCE_URL = "text/x-include-once-url"
    INCLUDE_URL = "text/x-include-url"


class CloudInitTemplate:
    def __init__(
        self,
    ) -> None:
        # Current submodule
        loader = jinja2.PackageLoader(
            package_name="orbitcloud_graviton.cloud_init", package_path="templates"
        )
        self.env = jinja2.Environment(loader=loader, autoescape=jinja2.select_autoescape())
        self.parts: list[ConfigPartArgs] = []

    def add(
        self, tpl: str, content_type: ContentType = ContentType.CONFIG, **kwargs
    ) -> ConfigPartArgs:
        _tpl: jinja2.Template = self.env.get_template(tpl)

        part = ConfigPartArgs(
            content=pulumi.Output.all(**kwargs).apply(func=lambda args: _tpl.render(args)),
            content_type=content_type,
            filename=tpl,
            merge_type="list(append)+dict(no_replace,recurse_list)+str()"
            if content_type == ContentType.JINJA2 or content_type == ContentType.CONFIG
            else None,
        )
        self.parts.append(part)
        return part
