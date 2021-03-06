# ActivitySim
# See full license in LICENSE.txt.

import logging
from collections import OrderedDict

import numpy as np
import pandas as pd

from activitysim.core import tracing
from activitysim.core import config
from activitysim.core import pipeline
from activitysim.core import simulate
from activitysim.core import inject

from activitysim.core.interaction_sample_simulate import interaction_sample_simulate
from activitysim.core.interaction_sample import interaction_sample

from activitysim.core.util import reindex
from activitysim.core.util import left_merge_on_index_and_col

from .util.logsums import compute_logsums
from .util.expressions import skim_time_period_label
from .util.logsums import mode_choice_logsums_spec

from .mode_choice import get_segment_and_unstack

"""
The school location model predicts the zones in which various people will
go to school.
"""

logger = logging.getLogger(__name__)
DUMP = False

# use int not str to identify school type in sample df
SCHOOL_TYPE_ID = OrderedDict([('university', 1), ('highschool', 2), ('gradeschool', 3)])


@inject.injectable()
def school_location_sample_spec(configs_dir):
    return simulate.read_model_spec(configs_dir, 'school_location_sample.csv')


@inject.injectable()
def school_location_settings(configs_dir):
    return config.read_model_settings(configs_dir, 'school_location.yaml')


@inject.injectable()
def school_location_spec(configs_dir):
    return simulate.read_model_spec(configs_dir, 'school_location.csv')


@inject.step()
def school_location_sample(
        persons_merged,
        school_location_sample_spec,
        school_location_settings,
        skim_dict,
        destination_size_terms,
        chunk_size,
        trace_hh_id):

    """
    build a table of persons * all zones to select a sample of alternative school locations.

    PERID,  dest_TAZ, rand,            pick_count
    23750,  14,       0.565502716034,  4
    23750,  16,       0.711135838871,  6
    ...
    23751,  12,       0.408038878552,  1
    23751,  14,       0.972732479292,  2
    """

    trace_label = 'school_location_sample'

    choosers = persons_merged.to_frame()
    alternatives = destination_size_terms.to_frame()

    constants = config.get_model_constants(school_location_settings)

    sample_size = school_location_settings["SAMPLE_SIZE"]
    alt_col_name = school_location_settings["ALT_COL_NAME"]

    logger.info("Running school_location_simulate with %d persons" % len(choosers))

    # create wrapper with keys for this lookup - in this case there is a TAZ in the choosers
    # and a TAZ in the alternatives which get merged during interaction
    # the skims will be available under the name "skims" for any @ expressions
    skims = skim_dict.wrap("TAZ", "TAZ_r")

    locals_d = {
        'skims': skims
    }
    if constants is not None:
        locals_d.update(constants)

    # FIXME - MEMORY HACK - only include columns actually used in spec
    chooser_columns = school_location_settings['SIMULATE_CHOOSER_COLUMNS']
    choosers = choosers[chooser_columns]

    choices_list = []
    for school_type, school_type_id in SCHOOL_TYPE_ID.iteritems():

        locals_d['segment'] = school_type

        choosers_segment = choosers[choosers["is_" + school_type]]

        # FIXME - no point in considering impossible alternatives
        alternatives_segment = alternatives[alternatives[school_type] > 0]

        logger.info("school_type %s:  %s persons %s alternatives" %
                    (school_type, len(choosers_segment), len(alternatives_segment)))

        if len(choosers_segment.index) > 0:

            choices = interaction_sample(
                choosers_segment,
                alternatives_segment,
                sample_size=sample_size,
                alt_col_name=alt_col_name,
                spec=school_location_sample_spec[[school_type]],
                skims=skims,
                locals_d=locals_d,
                chunk_size=chunk_size,
                trace_label=tracing.extend_trace_label(trace_label, school_type))

            choices['school_type'] = school_type_id
            choices_list.append(choices)

    choices = pd.concat(choices_list)

    # - # NARROW
    choices['school_type'] = choices['school_type'].astype(np.uint8)

    inject.add_table('school_location_sample', choices)


@inject.step()
def school_location_logsums(
        persons_merged,
        land_use,
        skim_dict, skim_stack,
        school_location_sample,
        configs_dir,
        chunk_size,
        trace_hh_id):

    """
    add logsum column to existing school_location_sample able

    logsum is calculated by running the mode_choice model for each sample (person, dest_taz) pair
    in school_location_sample, and computing the logsum of all the utilities

    +-------+--------------+----------------+------------+----------------+
    | PERID | dest_TAZ     | rand           | pick_count | logsum (added) |
    +=======+==============+================+============+================+
    | 23750 |  14          | 0.565502716034 | 4          |  1.85659498857 |
    +-------+--------------+----------------+------------+----------------+
    + 23750 | 16           | 0.711135838871 | 6          | 1.92315598631  |
    +-------+--------------+----------------+------------+----------------+
    + ...   |              |                |            |                |
    +-------+--------------+----------------+------------+----------------+
    | 23751 | 12           | 0.408038878552 | 1          | 2.40612135416  |
    +-------+--------------+----------------+------------+----------------+
    | 23751 | 14           | 0.972732479292 | 2          |  1.44009018355 |
    +-------+--------------+----------------+------------+----------------+
    """

    trace_label = 'school_location_logsums'

    school_location_settings = config.read_model_settings(configs_dir, 'school_location.yaml')

    alt_col_name = school_location_settings["ALT_COL_NAME"]
    chooser_col_name = 'TAZ'

    # FIXME - just using settings from tour_mode_choice
    logsum_settings = config.read_model_settings(configs_dir, 'tour_mode_choice.yaml')

    persons_merged = persons_merged.to_frame()
    school_location_sample = school_location_sample.to_frame()

    logger.info("Running school_location_logsums with %s rows" % school_location_sample.shape[0])

    # FIXME - MEMORY HACK - only include columns actually used in spec
    chooser_columns = school_location_settings['LOGSUM_CHOOSER_COLUMNS']
    persons_merged = persons_merged[chooser_columns]

    tracing.dump_df(DUMP, persons_merged, trace_label, 'persons_merged')

    logsums_list = []
    for school_type, school_type_id in SCHOOL_TYPE_ID.iteritems():

        logsums_spec = mode_choice_logsums_spec(configs_dir, school_type)

        choosers = school_location_sample[school_location_sample['school_type'] == school_type_id]

        choosers = pd.merge(
            choosers,
            persons_merged,
            left_index=True,
            right_index=True,
            how="left")

        choosers['in_period'] = skim_time_period_label(school_location_settings['IN_PERIOD'])
        choosers['out_period'] = skim_time_period_label(school_location_settings['OUT_PERIOD'])

        # FIXME - should do this in expression file?
        choosers['dest_topology'] = reindex(land_use.TOPOLOGY, choosers[alt_col_name])
        choosers['dest_density_index'] = reindex(land_use.density_index, choosers[alt_col_name])

        tracing.dump_df(DUMP, choosers,
                        tracing.extend_trace_label(trace_label, school_type),
                        'choosers')

        logsums = compute_logsums(
            choosers, logsums_spec, logsum_settings,
            skim_dict, skim_stack, chooser_col_name, alt_col_name, chunk_size,
            trace_hh_id,
            tracing.extend_trace_label(trace_label, school_type))

        logsums_list.append(logsums)

    logsums = pd.concat(logsums_list)

    # add_column series should have an index matching the table to which it is being added
    # logsums does, since school_location_sample was on left side of merge creating choosers
    inject.add_column("school_location_sample", "mode_choice_logsum", logsums)


@inject.step()
def school_location_simulate(persons_merged,
                             school_location_sample,
                             school_location_spec,
                             school_location_settings,
                             skim_dict,
                             destination_size_terms,
                             chunk_size,
                             trace_hh_id):
    """
    School location model on school_location_sample annotated with mode_choice logsum
    to select a school_taz from sample alternatives
    """

    choosers = persons_merged.to_frame()
    school_location_sample = school_location_sample.to_frame()
    destination_size_terms = destination_size_terms.to_frame()

    trace_label = 'school_location_simulate'
    alt_col_name = school_location_settings["ALT_COL_NAME"]

    constants = config.get_model_constants(school_location_settings)

    # create wrapper with keys for this lookup - in this case there is a TAZ in the choosers
    # and a TAZ in the alternatives which get merged during interaction
    # the skims will be available under the name "skims" for any @ expressions
    skims = skim_dict.wrap("TAZ", alt_col_name)

    locals_d = {
        'skims': skims,
    }
    if constants is not None:
        locals_d.update(constants)

    # FIXME - MEMORY HACK - only include columns actually used in spec
    chooser_columns = school_location_settings['SIMULATE_CHOOSER_COLUMNS']
    choosers = choosers[chooser_columns]
    tracing.dump_df(DUMP, choosers, 'school_location_simulate', 'choosers')

    choices_list = []
    for school_type, school_type_id in SCHOOL_TYPE_ID.iteritems():

        locals_d['segment'] = school_type

        choosers_segment = choosers[choosers["is_" + school_type]]
        alts_segment = \
            school_location_sample[school_location_sample['school_type'] == school_type_id]

        # alternatives are pre-sampled and annotated with logsums and pick_count
        # but we have to merge additional alt columns into alt sample list
        alts_segment = \
            pd.merge(alts_segment, destination_size_terms,
                     left_on=alt_col_name, right_index=True, how="left")

        tracing.dump_df(DUMP, alts_segment, trace_label, '%s_alternatives' % school_type)

        choices = interaction_sample_simulate(
            choosers_segment,
            alts_segment,
            spec=school_location_spec[[school_type]],
            choice_column=alt_col_name,
            skims=skims,
            locals_d=locals_d,
            chunk_size=chunk_size,
            trace_label=tracing.extend_trace_label(trace_label, school_type),
            trace_choice_name='school_location')

        choices_list.append(choices)

    choices = pd.concat(choices_list)

    # We only chose school locations for the subset of persons who go to school
    # so we backfill the empty choices with -1 to code as no school location
    choices = choices.reindex(persons_merged.index).fillna(-1).astype(int)

    tracing.dump_df(DUMP, choices, trace_label, 'choices')

    tracing.print_summary('school_taz', choices, describe=True)

    inject.add_column("persons", "school_taz", choices)

    pipeline.add_dependent_columns("persons", "persons_school")

    pipeline.drop_table('school_location_sample')

    if trace_hh_id:
        trace_columns = ['school_taz'] + inject.get_table('persons_school').columns
        tracing.trace_df(inject.get_table('persons_merged').to_frame(),
                         label="school_location",
                         columns=trace_columns,
                         warn_if_empty=True)
