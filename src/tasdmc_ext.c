// Python C extension wrapping C routines used in `tasdmc` package

#define PY_SSIZE_T_CLEAN
#include "Python.h"

#include "corsika_split_th.h"

static PyObject *
split_thinned_corsika_output(PyObject *self, PyObject *args)
{
    const char *corsika_particle_output_filename;
    int split_files_n;

    if (!PyArg_ParseTuple(args, "si", &corsika_particle_output_filename, &split_files_n))
        return NULL;

    int exit_code = splitThinnedCorsikaOutput(corsika_particle_output_filename, split_files_n);

    if (exit_code == EXIT_SUCCESS)
        Py_RETURN_NONE;
    else
    {
        PyErr_SetString(PyExc_IOError, "corsika_split_th failed to read or write some files");
        return NULL;
    }
}

static PyMethodDef methods[] = {
    {"split_thinned_corsika_output", (PyCFunction)split_thinned_corsika_output, METH_VARARGS, "split CORSIKA output for dethinning"},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

static struct PyModuleDef tasdmc_ext = {
    PyModuleDef_HEAD_INIT,
    "tasdmc_ext",
    "C extension module wrapping routines for TA SD MC",
    -1,
    methods,
};

PyMODINIT_FUNC PyInit_tasdmc_ext(void)
{
    return PyModule_Create(&tasdmc_ext);
}
