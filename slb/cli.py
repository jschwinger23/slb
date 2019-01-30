import click

from slb.common.utils import URL
from slb.common.click import UrlType
from slb.nginx.utils import NginxPrinter
from slb.nginx.models import NginxProject, NginxProject


@click.group(context_settings=dict(help_option_names=['-h', '--help']))
def main():
    pass


@main.group()
@click.argument('url', type=UrlType)
@click.pass_context
def url(ctx, url: URL):
    project = NginxProject.get_by_url(url)
    ctx.obj = {
        'url': url,
        'server': project.servers.get(
            server_name=url.netloc, ports__contains=url.port
        )
    }


@url.command()
@click.pass_context
@click.option('--upstream', '-u', is_flag=True)
def inspect(ctx, upstream=False):
    url, server = ctx.obj['url'], ctx.obj['server']
    location = server.get_location(url)
    click.secho(f'location: {location.path}', fg='green')
    click.secho(f'proxy_pass: {location.proxy_pass.value}', fg='green')
    if upstream:
        click.secho(f'upstream: {location.proxy_pass.upstream}', fg='green')


@url.command()
@click.option('--vhost', '-s', is_flag=True)
@click.option('--pretty', '-p', is_flag=True)
@click.pass_context
def conf(ctx, vhost=False, pretty=False):
    url, server = ctx.obj['url'], ctx.obj['server']
    conf = server
    if not vhost:
        conf = server.find_location(url)
    NginxPrinter(pretty=pretty).print(conf)


@main.command()
@click.argument('filename')
def fmt(filename):
    project = NginxProject.from_file(filename)
    NginxPrinter(pretty=True).print(project)
