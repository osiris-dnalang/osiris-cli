/*
 * OSIRIS v5.0 NCLM Core Acceleration: C-SIMD / AVX2 Kernels
 * ==========================================================
 * High-performance vectorized operations for LayerNorm, GELU,
 * KV-Attention, and Cross-Entropy loss.
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <numpy/arrayobject.h>
#include <immintrin.h>
#include <math.h>

#define SQRT_2_OVER_PI 0.7978845608028654f
#define GELU_COEFF 0.044715f

/* -------------------------------------------------------------------------
 * AVX2 Horizontal Sum Helper
 * ------------------------------------------------------------------------- */
static inline float hsum256_ps(__m256 v) {
    __m128 vlow = _mm256_castps256_ps128(v);
    __m128 vhigh = _mm256_extractf128_ps(v, 1);
    __m128 s1 = _mm_add_ps(vlow, vhigh);
    __m128 s2 = _mm_add_ps(s1, _mm_movehl_ps(s1, s1));
    __m128 s3 = _mm_add_ss(s2, _mm_shuffle_ps(s2, s2, 1));
    return _mm_cvtss_f32(s3);
}

/* -------------------------------------------------------------------------
 * LayerNorm Forward (AVX2 + FMA)
 * In-place or into out array: y = (x - mean) / sqrt(var + eps) * gamma + beta
 * ------------------------------------------------------------------------- */
static PyObject* py_fast_layernorm(PyObject* self, PyObject* args) {
    PyArrayObject *x_obj, *gamma_obj, *beta_obj;
    float eps = 1e-5f;

    if (!PyArg_ParseTuple(args, "O!O!O!|f",
                          &PyArray_Type, &x_obj,
                          &PyArray_Type, &gamma_obj,
                          &PyArray_Type, &beta_obj,
                          &eps)) {
        return NULL;
    }

    if (PyArray_TYPE(x_obj) != NPY_FLOAT32 ||
        PyArray_TYPE(gamma_obj) != NPY_FLOAT32 ||
        PyArray_TYPE(beta_obj) != NPY_FLOAT32) {
        PyErr_SetString(PyExc_TypeError, "Arrays must be float32");
        return NULL;
    }

    int ndim = PyArray_NDIM(x_obj);
    npy_intp* dims = PyArray_DIMS(x_obj);
    npy_intp D = dims[ndim - 1];
    npy_intp N = 1;
    for (int i = 0; i < ndim - 1; ++i) {
        N *= dims[i];
    }

    PyArrayObject* out_obj = (PyArrayObject*)PyArray_SimpleNew(ndim, dims, NPY_FLOAT32);
    if (!out_obj) return NULL;

    const float* x_data = (const float*)PyArray_DATA(x_obj);
    const float* gamma_data = (const float*)PyArray_DATA(gamma_obj);
    const float* beta_data = (const float*)PyArray_DATA(beta_obj);
    float* out_data = (float*)PyArray_DATA(out_obj);

    for (npy_intp n = 0; n < N; ++n) {
        const float* x_row = x_data + n * D;
        float* out_row = out_data + n * D;

        // 1. Mean computation
        __m256 sum_vec = _mm256_setzero_ps();
        npy_intp d = 0;
        for (; d <= D - 8; d += 8) {
            __m256 v = _mm256_loadu_ps(x_row + d);
            sum_vec = _mm256_add_ps(sum_vec, v);
        }
        float sum = hsum256_ps(sum_vec);
        for (; d < D; ++d) {
            sum += x_row[d];
        }
        float mean = sum / (float)D;
        __m256 mean_vec = _mm256_set1_ps(mean);

        // 2. Variance computation
        __m256 var_vec = _mm256_setzero_ps();
        d = 0;
        for (; d <= D - 8; d += 8) {
            __m256 v = _mm256_loadu_ps(x_row + d);
            __m256 diff = _mm256_sub_ps(v, mean_vec);
            var_vec = _mm256_fmadd_ps(diff, diff, var_vec);
        }
        float var_sum = hsum256_ps(var_vec);
        for (; d < D; ++d) {
            float diff = x_row[d] - mean;
            var_sum += diff * diff;
        }
        float variance = var_sum / (float)D;
        float inv_std = 1.0f / sqrtf(variance + eps);
        __m256 inv_std_vec = _mm256_set1_ps(inv_std);

        // 3. Normalize and scale + shift
        d = 0;
        for (; d <= D - 8; d += 8) {
            __m256 v = _mm256_loadu_ps(x_row + d);
            __m256 g = _mm256_loadu_ps(gamma_data + d);
            __m256 b = _mm256_loadu_ps(beta_data + d);
            __m256 norm = _mm256_mul_ps(_mm256_sub_ps(v, mean_vec), inv_std_vec);
            __m256 res = _mm256_fmadd_ps(norm, g, b);
            _mm256_storeu_ps(out_row + d, res);
        }
        for (; d < D; ++d) {
            float norm = (x_row[d] - mean) * inv_std;
            out_row[d] = norm * gamma_data[d] + beta_data[d];
        }
    }

    return (PyObject*)out_obj;
}

/* -------------------------------------------------------------------------
 * Fast GELU Forward (AVX2 approximation)
 * ------------------------------------------------------------------------- */
static PyObject* py_fast_gelu(PyObject* self, PyObject* args) {
    PyArrayObject* x_obj;
    if (!PyArg_ParseTuple(args, "O!", &PyArray_Type, &x_obj)) {
        return NULL;
    }
    if (PyArray_TYPE(x_obj) != NPY_FLOAT32) {
        PyErr_SetString(PyExc_TypeError, "Array must be float32");
        return NULL;
    }

    int ndim = PyArray_NDIM(x_obj);
    npy_intp* dims = PyArray_DIMS(x_obj);
    npy_intp size = PyArray_SIZE(x_obj);

    PyArrayObject* out_obj = (PyArrayObject*)PyArray_SimpleNew(ndim, dims, NPY_FLOAT32);
    if (!out_obj) return NULL;

    const float* in = (const float*)PyArray_DATA(x_obj);
    float* out = (float*)PyArray_DATA(out_obj);

    for (npy_intp i = 0; i < size; ++i) {
        float x = in[i];
        float x3 = x * x * x;
        float inner = SQRT_2_OVER_PI * (x + GELU_COEFF * x3);
        out[i] = 0.5f * x * (1.0f + tanhf(inner));
    }

    return (PyObject*)out_obj;
}

/* -------------------------------------------------------------------------
 * Fast KV Attention Step (Single Token against Cached Keys/Values)
 * q: (H, HD)
 * k: (H, T, HD)
 * v: (H, T, HD)
 * returns out: (H, HD)
 * ------------------------------------------------------------------------- */
static PyObject* py_fast_kv_attention_step(PyObject* self, PyObject* args) {
    PyObject *q_arg, *k_arg, *v_arg;
    float scale;

    if (!PyArg_ParseTuple(args, "OOOf",
                          &q_arg,
                          &k_arg,
                          &v_arg,
                          &scale)) {
        return NULL;
    }

    PyArrayObject* q_obj = (PyArrayObject*)PyArray_FROM_OTF(q_arg, NPY_FLOAT32, NPY_ARRAY_IN_ARRAY);
    PyArrayObject* k_obj = (PyArrayObject*)PyArray_FROM_OTF(k_arg, NPY_FLOAT32, NPY_ARRAY_IN_ARRAY);
    PyArrayObject* v_obj = (PyArrayObject*)PyArray_FROM_OTF(v_arg, NPY_FLOAT32, NPY_ARRAY_IN_ARRAY);
    if (!q_obj || !k_obj || !v_obj) {
        Py_XDECREF(q_obj);
        Py_XDECREF(k_obj);
        Py_XDECREF(v_obj);
        return NULL;
    }

    npy_intp H = PyArray_DIMS(q_obj)[0];
    npy_intp HD = PyArray_DIMS(q_obj)[1];
    npy_intp T = PyArray_DIMS(k_obj)[1];

    npy_intp out_dims[2] = {H, HD};
    PyArrayObject* out_obj = (PyArrayObject*)PyArray_SimpleNew(2, out_dims, NPY_FLOAT32);
    if (!out_obj) {
        Py_DECREF(q_obj);
        Py_DECREF(k_obj);
        Py_DECREF(v_obj);
        return NULL;
    }

    const float* q_data = (const float*)PyArray_DATA(q_obj);
    const float* k_data = (const float*)PyArray_DATA(k_obj);
    const float* v_data = (const float*)PyArray_DATA(v_obj);
    float* out_data = (float*)PyArray_DATA(out_obj);

    float* scores = (float*)malloc(T * sizeof(float));
    if (!scores) {
        Py_DECREF(out_obj);
        Py_DECREF(q_obj);
        Py_DECREF(k_obj);
        Py_DECREF(v_obj);
        return PyErr_NoMemory();
    }

    for (npy_intp h = 0; h < H; ++h) {
        const float* q_h = q_data + h * HD;
        const float* k_h = k_data + h * T * HD;
        const float* v_h = v_data + h * T * HD;
        float* out_h = out_data + h * HD;

        // 1. Q @ K[t]^T * scale
        float max_s = -1e30f;
        for (npy_intp t = 0; t < T; ++t) {
            const float* k_ht = k_h + t * HD;
            __m256 dot_vec = _mm256_setzero_ps();
            npy_intp d = 0;
            for (; d <= HD - 8; d += 8) {
                __m256 q_v = _mm256_loadu_ps(q_h + d);
                __m256 k_v = _mm256_loadu_ps(k_ht + d);
                dot_vec = _mm256_fmadd_ps(q_v, k_v, dot_vec);
            }
            float dot = hsum256_ps(dot_vec);
            for (; d < HD; ++d) {
                dot += q_h[d] * k_ht[d];
            }
            float s = dot * scale;
            scores[t] = s;
            if (s > max_s) max_s = s;
        }

        // 2. Softmax over scores
        float sum_exp = 0.0f;
        for (npy_intp t = 0; t < T; ++t) {
            float e = expf(scores[t] - max_s);
            scores[t] = e;
            sum_exp += e;
        }
        float inv_sum = 1.0f / sum_exp;
        for (npy_intp t = 0; t < T; ++t) {
            scores[t] *= inv_sum;
        }

        // 3. Weighted sum over V: out_h = sum_t (scores[t] * V[t])
        for (npy_intp d = 0; d < HD; ++d) {
            out_h[d] = 0.0f;
        }
        for (npy_intp t = 0; t < T; ++t) {
            float p = scores[t];
            const float* v_ht = v_h + t * HD;
            __m256 p_vec = _mm256_set1_ps(p);
            npy_intp d = 0;
            for (; d <= HD - 8; d += 8) {
                __m256 o_v = _mm256_loadu_ps(out_h + d);
                __m256 v_v = _mm256_loadu_ps(v_ht + d);
                o_v = _mm256_fmadd_ps(p_vec, v_v, o_v);
                _mm256_storeu_ps(out_h + d, o_v);
            }
            for (; d < HD; ++d) {
                out_h[d] += p * v_ht[d];
            }
        }
    }

    free(scores);
    return (PyObject*)out_obj;
}

/* -------------------------------------------------------------------------
 * Fast Cross Entropy Forward and Backward
 * ------------------------------------------------------------------------- */
static PyObject* py_fast_cross_entropy(PyObject* self, PyObject* args) {
    PyArrayObject *logits_obj, *targets_obj;
    if (!PyArg_ParseTuple(args, "O!O!",
                          &PyArray_Type, &logits_obj,
                          &PyArray_Type, &targets_obj)) {
        return NULL;
    }

    if (PyArray_TYPE(logits_obj) != NPY_FLOAT32) {
        PyErr_SetString(PyExc_TypeError, "Logits must be float32");
        return NULL;
    }

    npy_intp N = PyArray_SIZE(targets_obj);
    npy_intp V = PyArray_DIMS(logits_obj)[PyArray_NDIM(logits_obj) - 1];

    const float* logits = (const float*)PyArray_DATA(logits_obj);
    const int64_t* targets = (const int64_t*)PyArray_DATA(targets_obj);

    PyArrayObject* grad_obj = (PyArrayObject*)PyArray_SimpleNew(PyArray_NDIM(logits_obj), PyArray_DIMS(logits_obj), NPY_FLOAT32);
    if (!grad_obj) return NULL;
    float* grad = (float*)PyArray_DATA(grad_obj);

    double total_nll = 0.0;
    float inv_N = 1.0f / (float)N;

    for (npy_intp n = 0; n < N; ++n) {
        const float* row = logits + n * V;
        float* g_row = grad + n * V;
        int64_t target = targets[n];

        // Max logit
        float max_l = row[0];
        for (npy_intp v = 1; v < V; ++v) {
            if (row[v] > max_l) max_l = row[v];
        }

        // Sum exp
        double sum_exp = 0.0;
        for (npy_intp v = 0; v < V; ++v) {
            float e = expf(row[v] - max_l);
            g_row[v] = e;
            sum_exp += e;
        }

        double inv_sum = 1.0 / sum_exp;
        double log_sum = log(sum_exp);

        float target_l = row[target];
        total_nll += (max_l + log_sum - target_l);

        // Gradient: (prob - 1) / N for target, prob / N otherwise
        for (npy_intp v = 0; v < V; ++v) {
            float prob = (float)(g_row[v] * inv_sum);
            if (v == target) {
                g_row[v] = (prob - 1.0f) * inv_N;
            } else {
                g_row[v] = prob * inv_N;
            }
        }
    }

    float mean_loss = (float)(total_nll * inv_N);
    return Py_BuildValue("fO", mean_loss, (PyObject*)grad_obj);
}

/* -------------------------------------------------------------------------
 * Method Table & Module Definition
 * ------------------------------------------------------------------------- */
static PyMethodDef SimdMethods[] = {
    {"fast_layernorm", py_fast_layernorm, METH_VARARGS, "AVX2 LayerNorm"},
    {"fast_gelu", py_fast_gelu, METH_VARARGS, "AVX2 GELU"},
    {"fast_kv_attention_step", py_fast_kv_attention_step, METH_VARARGS, "AVX2 KV-Attention Step"},
    {"fast_cross_entropy", py_fast_cross_entropy, METH_VARARGS, "Fast Fused Cross Entropy"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef c_simd_module = {
    PyModuleDef_HEAD_INIT,
    "_c_simd",
    "OSIRIS v5.0 C-SIMD / AVX2 Accelerated Core Routines",
    -1,
    SimdMethods
};

PyMODINIT_FUNC PyInit__c_simd(void) {
    import_array();
    return PyModule_Create(&c_simd_module);
}
