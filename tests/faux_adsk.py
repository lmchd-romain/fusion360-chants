"""Faux module adsk (adsk, adsk.core, adsk.fusion) pour charger l'add-in hors de Fusion."""
import sys
import types
from unittest import mock


class _Castable:
    @classmethod
    def cast(cls, objet):
        return objet if isinstance(objet, cls) else None


def installer():
    adsk = types.ModuleType("adsk")
    core = types.ModuleType("adsk.core")
    fusion = types.ModuleType("adsk.fusion")
    for nom in ("CommandCreatedEventHandler", "InputChangedEventHandler", "ValidateInputsEventHandler",
                "CommandEventHandler", "HTMLEventHandler", "SelectionEventHandler"):
        setattr(core, nom, type(nom, (), {"__init__": lambda self: None}))
    for nom in ("Line3D", "Arc3D", "ColorProperty"):
        setattr(core, nom, type(nom, (_Castable,), {}))
    for nom in ("BRepFace", "BRepBody", "Occurrence"):
        setattr(fusion, nom, type(nom, (_Castable,), {}))
    app = mock.MagicMock(name="app")
    core.Application = mock.MagicMock()
    core.Application.get.return_value = app
    for nom in ("UserLanguages", "DropDownStyles", "ValueInput", "SurfaceTypes", "Matrix3D", "Vector3D", "Point3D",
                "Point2D", "ObjectCollection", "UserInterfaceThemes", "Color", "DocumentTypes"):
        setattr(core, nom, mock.MagicMock(name=nom))
    for nom in ("Design", "FeatureOperations", "CustomGraphicsCoordinates", "CustomGraphicsSolidColorEffect",
                "TriangleMeshQualityOptions", "PointContainment", "DesignTypes"):
        setattr(fusion, nom, mock.MagicMock(name=nom))
    adsk.core, adsk.fusion = core, fusion
    adsk.doEvents = lambda: None
    sys.modules.update({"adsk": adsk, "adsk.core": core, "adsk.fusion": fusion})
    return app


def retirer():
    for n in ("adsk", "adsk.core", "adsk.fusion"):
        sys.modules.pop(n, None)
