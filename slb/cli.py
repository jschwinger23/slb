import re
import click

from .utils import URL, UrlType, LB, NginxConf


@click.group(context_settings=dict(help_option_names=['-h', '--help']))
def main():
    pass


@main.group()
@click.argument('url', type=UrlType)
@click.pass_context
def url(ctx, url: URL):
    ctx.obj = {'url': url}


@url.command()
@click.pass_context
def inspect(ctx):
    url = ctx.obj['url']
    lb = LB(url.env, url.cid)
    conf_filename = lb.run(
        f'grep {url.netloc} -r /etc/nginx/http-enabled/ -l | grep -v dyupstream'
    )
    click.secho(f'conf_file: {conf_filename}')
    conf_content = lb.run(f'cat {conf_filename}')
    nginx_conf = NginxConf(conf_content)
    location = nginx_conf.find_location(url)
    click.secho(f'location: {location.value}')
    proxy_pass = next(d for d in location.children if d.name == 'proxy_pass')
    click.secho(f'proxy_pass: {proxy_pass.value}')
    proxy_pass = re.search('://(.+)', proxy_pass.value).group(1)
    click.secho(
        lb.run(
            f'grep {proxy_pass} -r /etc/nginx/service_deps/services.json /etc/nginx/http-enabled/dyupstream* -A5'
        ),
        fg='green'
    )


@url.command()
@click.pass_context
def conf(ctx):
    url = ctx.obj['url']
    lb = LB(url.env, url.cid)
    conf_filename = lb.run(
        f'grep {url.netloc} -r /etc/nginx/http-enabled/ -l | grep -v dyupstream'
    )
    click.secho(f'conf_file: {conf_filename}')
    nginx_conf = NginxConf(lb.run(f'cat {conf_filename}'))
    if url.path:
        location = nginx_conf.find_location(url)
        for l in location.as_strings:
            print(l)
    else:
        server = nginx_conf.find_server(url)
        for l in server.as_strings:
            print(l)


@main.command()
@click.argument('filename')
def fmt(filename):
    nginx_conf = NginxConf.from_file(filename)
    print(nginx_conf.format())
