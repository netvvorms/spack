import spack.modules


def post_install(pkg):
    dk = spack.modules.LmodModule(pkg.spec)
    dk.write()


def post_uninstall(pkg):
    dk = spack.modules.LmodModule(pkg.spec)
    dk.remove()
