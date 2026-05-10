from __future__ import annotations

from functools import lru_cache
from typing import Any

try:
    from rdkit import Chem, DataStructs
    from rdkit.Chem import AllChem, Crippen, Descriptors, Lipinski, rdMolDescriptors

    try:
        from rdkit.Chem import rdFingerprintGenerator
    except ImportError:  # pragma: no cover - older RDKit fallback
        rdFingerprintGenerator = None
except ImportError:  # pragma: no cover - exercised only without optional dependency
    Chem = None
    DataStructs = None
    AllChem = None
    Crippen = None
    Descriptors = None
    Lipinski = None
    rdMolDescriptors = None
    rdFingerprintGenerator = None


def rdkit_available() -> bool:
    return Chem is not None


def require_rdkit() -> None:
    if Chem is None:
        raise RuntimeError("RDKit is required for chemistry descriptors and constraints")


@lru_cache(maxsize=100_000)
def mol_from_smiles(smiles: str) -> Any:
    require_rdkit()
    return Chem.MolFromSmiles(smiles)


def canonicalize_smiles(smiles: str) -> str | None:
    mol = mol_from_smiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)


def compute_descriptors(smiles: str) -> dict[str, float | int | bool | None]:
    mol = mol_from_smiles(smiles)
    if mol is None:
        return {
            "valid_smiles": False,
            "mw": None,
            "clogp": None,
            "tpsa": None,
            "hbd": None,
            "hba": None,
            "rotatable_bonds": None,
            "heavy_atoms": None,
        }
    return {
        "valid_smiles": True,
        "canonical_smiles": canonicalize_smiles(smiles),
        "mw": float(Descriptors.MolWt(mol)),
        "clogp": float(Crippen.MolLogP(mol)),
        "tpsa": float(rdMolDescriptors.CalcTPSA(mol)),
        "hbd": int(Lipinski.NumHDonors(mol)),
        "hba": int(Lipinski.NumHAcceptors(mol)),
        "rotatable_bonds": int(Lipinski.NumRotatableBonds(mol)),
        "heavy_atoms": int(mol.GetNumHeavyAtoms()),
    }


@lru_cache(maxsize=100_000)
def morgan_fingerprint(smiles: str, radius: int = 2, n_bits: int = 2048) -> Any:
    mol = mol_from_smiles(smiles)
    if mol is None:
        return None
    if rdFingerprintGenerator is not None:
        generator = rdFingerprintGenerator.GetMorganGenerator(radius=radius, fpSize=n_bits)
        return generator.GetFingerprint(mol)
    return AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)


def tanimoto_similarity(smiles_a: str, smiles_b: str) -> float | None:
    require_rdkit()
    fp_a = morgan_fingerprint(smiles_a)
    fp_b = morgan_fingerprint(smiles_b)
    if fp_a is None or fp_b is None:
        return None
    return float(DataStructs.TanimotoSimilarity(fp_a, fp_b))


def fingerprint_bits(smiles: str, radius: int = 2, n_bits: int = 2048) -> list[int]:
    fp = morgan_fingerprint(smiles, radius=radius, n_bits=n_bits)
    if fp is None:
        return [0] * n_bits
    return [int(bit) for bit in fp.ToBitString()]
