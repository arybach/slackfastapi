# jinja_processing.py
import argparse
import os

import jinja2


def process_templates(app_image_tag, num_replicas, namespace_name):
    """Process Jinja2 templates for Kubernetes manifests."""
    template_loader = jinja2.FileSystemLoader(searchpath="./deploy/kube/templates/")
    template_env = jinja2.Environment(loader=template_loader)

    app_template = template_env.get_template("app.yml.j2")
    db_template = template_env.get_template("db.yml.j2")
    namespace_template = template_env.get_template("namespace.yml.j2")

    output_app = app_template.render(app_image=app_image_tag, num_replicas=num_replicas)
    output_db = db_template.render(db_image=app_image_tag)
    output_namespace = namespace_template.render(namespace_name=namespace_name)

    with open("./deploy/kube/app.yml", "w") as f:
        f.write(output_app)

    with open("./deploy/kube/db.yml", "w") as f:
        f.write(output_db)

    with open("./deploy/kube/namespace.yml", "w") as f:
        f.write(output_namespace)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process Jinja2 templates for Kubernetes manifests.",
    )
    parser.add_argument(
        "--num_replicas",
        type=int,
        help="Number of replicas for the deployment",
        default=2,
    )
    parser.add_argument("--namespace", help="Kubernetes namespace", default="staging")
    args = parser.parse_args()

    app_image_tag = (
        os.environ["CI_REGISTRY_IMAGE"]
        + ":"
        + args.namespace
        + "-"
        + os.environ["CI_COMMIT_REF_SLUG"]
    )
    process_templates(app_image_tag, args.num_replicas, args.namespace)
