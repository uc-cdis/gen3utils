import logging

import click
import pkg_resources

logging.basicConfig()


@click.group()
def main():
    """Utils for Gen3 cdis-manifest management."""


for ep in pkg_resources.iter_entry_points("gen3utils.commands"):
    try:
        ep.load()
    except pkg_resources.DistributionNotFound:
        pass


if __name__ == "__main__":
    main()
