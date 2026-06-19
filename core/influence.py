"""Post-deletion t-value computation using OLS exact diagnostic formulas.

Core formula (from technical doc §4.1):
    tbeta_hat^(i)_j = beta_hatbeta_hat^(i)_j / sqrt(sigma^2_(i) ? [(X'X)^(-1)]_{jj})

where beta_hatbeta_hat^(i)_j = params_not_obsi[i, j].
Sorting target is t-value, NOT beta alone (correcting Stata defect).
"""

import numpy as np


def compute_deletion_t_values(
    params_not_obsi: np.ndarray,
    sigma2_not_obsi: np.ndarray,
    XtX_inv_diag: np.ndarray,
    key_var_index: int,
) -> np.ndarray:
    """Compute post-deletion t-values for the key variable for every observation.

    tbeta_hat = beta_hatbeta_hat^(i)_j / sqrt(??_(i) ? [(X'X)^(-1)]_{jj})

    Args:
        params_not_obsi: (N, K) array; beta_hat^(i) for each observation.
        sigma2_not_obsi: (N,) array; ?? estimate with obs i removed.
        XtX_inv_diag: (K,) array; diagonal of (X''X)???.
        key_var_index: Column index of the key variable in the design matrix.

    Returns:
        (N,) array of post-deletion t-values for the key variable.
    """
    beta_del = params_not_obsi[:, key_var_index]
    se_del = np.sqrt(sigma2_not_obsi * XtX_inv_diag[key_var_index])
    t_del = beta_del / se_del
    return t_del


def compute_deletion_dfbeta(
    beta_vector: np.ndarray,
    params_not_obsi: np.ndarray,
    key_var_index: int,
) -> np.ndarray:
    """Compute raw DFBETA (coefficient change) for the key variable.

    dfbeta_i = beta_hat_j - beta_hatbeta_hat^(i)_j

    Args:
        beta_vector: (K,) array; full-sample coefficient estimates.
        params_not_obsi: (N, K) array; leave-one-out coefficient estimates.
        key_var_index: Column index of the key variable.

    Returns:
        (N,) array of raw DFBETA values for the key variable.
    """
    beta_key = beta_vector[key_var_index]
    return beta_key - params_not_obsi[:, key_var_index]


def sort_by_t_impact(
    t_values: np.ndarray,
    active_mask: np.ndarray,
    ascending: bool = False,
) -> np.ndarray:
    """Sort observation indices by their post-deletion t-value.

    Args:
        t_values: (N,) post-deletion t-values.
        active_mask: (N,) boolean mask; True = observation still in play.
        ascending: If False (default), returns indices with highest t first.

    Returns:
        Array of indices sorted by t-value, considering only active observations.
    """
    # Mask inactive observations with -inf (descending) or +inf (ascending)
    if ascending:
        sort_vals = np.where(active_mask, t_values, np.inf)
    else:
        sort_vals = np.where(active_mask, t_values, -np.inf)

    return np.argsort(sort_vals)[::-1] if not ascending else np.argsort(sort_vals)
