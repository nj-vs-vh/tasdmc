// Python C extension wrapping C routines used in `tasdmc` package

#define PY_SSIZE_T_CLEAN
#include "Python.h"

#include "corsika_split_th.h"
#include "./dethinning/main.h"
#include "./corsika2geant/main.h"

static PyObject *
split_thinned_corsika_output(PyObject *self, PyObject *args)
{
    const char *corsika_particle_filename;
    int split_files_n;

    if (!PyArg_ParseTuple(args, "si", &corsika_particle_filename, &split_files_n))
        return NULL;

    int exit_code = splitThinnedCorsikaOutput(corsika_particle_filename, split_files_n);

    if (exit_code == EXIT_SUCCESS)
        Py_RETURN_NONE;
    else
    {
        PyErr_SetString(PyExc_Exception, "corsika_split_th failed to read or write some files");
        return NULL;
    }
}


static PyObject *
run_dethinning(PyObject *self, PyObject *args)
{
    const char *particle_filename;
    const char *longtitude_filename;
	const char *output_filename;

    if (!PyArg_ParseTuple(args, "sss", &particle_filename, &longtitude_filename, &output_filename))
        return NULL;

    int exit_code = dethinning(particle_filename, longtitude_filename, output_filename, true);

    if (exit_code == EXIT_SUCCESS)
        Py_RETURN_NONE;
    else
    {
        PyErr_SetString(PyExc_Exception, "dethinning failed, see stderr");
        return NULL;
    }
}


static PyObject *
run_c2g(PyObject *self, PyObject *args)
{
    const char *particle_filelist;
    const char *geant_filename;
	const char *output_filename;

    if (!PyArg_ParseTuple(args, "sss", &particle_filelist, &geant_filename, &output_filename))
        return NULL;

    int exit_code = corsika2geant(particle_filelist, geant_filename, output_filename);

    if (exit_code == EXIT_SUCCESS)
        Py_RETURN_NONE;
    else
    {
        PyErr_SetString(PyExc_Exception, "corsika2geant failed, see stderr");
        return NULL;
    }
}


static PyMethodDef methods[] = {
    {"split_thinned_corsika_output", (PyCFunction)split_thinned_corsika_output, METH_VARARGS, "split CORSIKA output for dethinning"},
    {"run_dethinning", (PyCFunction)run_dethinning, METH_VARARGS, "run dethinning C routine on particle file"},
    {"run_corsika2geant", (PyCFunction)run_c2g, METH_VARARGS, "run corsika2geant C routine on a list of particle files"},
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
