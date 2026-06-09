"""
License Stub — Placeholder pour injection de licence

Ce fichier est compilé dans le build de base.
Il contient le placeholder qui sera remplacé par la vraie licence
au moment de la génération du build client.

NE PAS MODIFIER LE CONTENU DE CETTE VARIABLE MANUELLEMENT.
"""

# Ce placeholder est recherché dans le binaire par build_generator.py
# et remplacé par la licence unique du client.
_LICENSE_STUB = "__LICENSE_PLACEHOLDER__" + "_" * 32

def get_license_stub():
    """Retourne le placeholder (pour vérification interne)."""
    return _LICENSE_STUB
