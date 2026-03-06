import reflex as rx

config = rx.Config(
    app_name="ssecur1",
    app_module_import="app",
    plugins=[rx.plugins.SitemapPlugin()],
)
