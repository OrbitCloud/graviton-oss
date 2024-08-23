import base64

import jinja2
import pulumi


class JinjaTemplate:
    def __init__(
        self,
        template_relative_path: str,
        search_path: str,
    ) -> None:
        loader = jinja2.FileSystemLoader(searchpath=search_path)
        env = jinja2.Environment(loader=loader)
        self.template: jinja2.Template = env.get_template(template_relative_path)

    def base64(self, value: str) -> str:
        return base64.b64encode(value.encode(encoding="utf-8")).decode(encoding="utf-8")

    def output(self, **kwargs) -> pulumi.Output[str]:
        return pulumi.Output.all(**kwargs).apply(func=lambda args: self.template.render(args))

    def output_base64(self, **kwargs) -> pulumi.Output[str]:
        return pulumi.Output.all(**kwargs).apply(
            func=lambda args: self.base64(value=self.template.render(args))
        )
