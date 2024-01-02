#!/usr/bin/env python3
# Copyright 2010-2022 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Creates a shift scheduling problem and solves it."""

#from absl import app
#from absl import flags

#from google.protobuf import text_format
from ortools.sat.python import cp_model
import json
import sys
import math
import time

#_OUTPUT_PROTO = flags.DEFINE_string(
#    "output_proto", "", "Output file to write the cp_model proto to."
#)
#_PARAMS = flags.DEFINE_string(
#    "params", "max_time_in_seconds:10.0", "Sat solver parameters."
#)


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Display the objective value and time of intermediate solutions."""

    def __init__(self):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__solution_count = 0
        self.__start_time = time.time()

    def on_solution_callback(self):
        """Called on each new solution."""
        current_time = time.time()
        obj = self.ObjectiveValue()
        sys.stderr.write('Solution %i, time = %0.2f s, objective = %i\n' %
              (self.__solution_count, current_time - self.__start_time, obj))
        self.__solution_count += 1

    def solution_count(self):
        """Returns the number of solutions found."""
        return self.__solution_count


def negated_bounded_span(
    works, start: int, length: int
):
    """Filters an isolated sub-sequence of variables assined to True.

    Extract the span of Boolean variables [start, start + length), negate them,
    and if there is variables to the left/right of this span, surround the span by
    them in non negated form.

    Args:
      works: a list of variables to extract the span from.
      start: the start to the span.
      length: the length of the span.

    Returns:
      a list of variables which conjunction will be false if the sub-list is
      assigned to True, and correctly bounded by variables assigned to False,
      or by the start or end of works.
    """
    sequence = []
    # left border (start of works, or works[start - 1])
    if start > 0:
        sequence.append(works[start - 1])
    for i in range(length):
        sequence.append(works[start + i].Not())
    # right border (end of works or works[start + length])
    if start + length < len(works):
        sequence.append(works[start + length])
    return sequence


def add_soft_sequence_constraint(
    model,
    works,
        hard_min,
    soft_min,
    min_cost,
    soft_max,
    hard_max,
    max_cost,
    prefix,
):
    """Sequence constraint on true variables with soft and hard bounds.

    This constraint look at every maximal contiguous sequence of variables
    assigned to true. If forbids sequence of length < hard_min or > hard_max.
    Then it creates penalty terms if the length is < soft_min or > soft_max.

    Args:
      model: the sequence constraint is built on this model.
      works: a list of Boolean variables.
      hard_min: any sequence of true variables must have a length of at least
        hard_min.
      soft_min: any sequence should have a length of at least soft_min, or a
        linear penalty on the delta will be added to the objective.
      min_cost: the coefficient of the linear penalty if the length is less than
        soft_min.
      soft_max: any sequence should have a length of at most soft_max, or a linear
        penalty on the delta will be added to the objective.
      hard_max: any sequence of true variables must have a length of at most
        hard_max.
      max_cost: the coefficient of the linear penalty if the length is more than
        soft_max.
      prefix: a base name for penalty literals.

    Returns:
      a tuple (variables_list, coefficient_list) containing the different
      penalties created by the sequence constraint.
    """
    cost_literals = []
    cost_coefficients = []

    # Forbid sequences that are too short.
    for length in range(1, hard_min):
        for start in range(len(works) - length + 1):
            model.AddBoolOr(negated_bounded_span(works, start, length))

    # Penalize sequences that are below the soft limit.
    if min_cost > 0:
        for length in range(hard_min, soft_min):
            for start in range(len(works) - length + 1):
                span = negated_bounded_span(works, start, length)
                name = ": under_span(start=%i, length=%i)" % (start, length)
                lit = model.NewBoolVar(prefix + name)
                span.append(lit)
                model.AddBoolOr(span)
                cost_literals.append(lit)
                # We filter exactly the sequence with a short length.
                # The penalty is proportional to the delta with soft_min.
                cost_coefficients.append(min_cost * (soft_min - length))

    # Penalize sequences that are above the soft limit.
    if max_cost > 0:
        for length in range(soft_max + 1, hard_max + 1):
            for start in range(len(works) - length + 1):
                span = negated_bounded_span(works, start, length)
                name = ": over_span(start=%i, length=%i)" % (start, length)
                lit = model.NewBoolVar(prefix + name)
                span.append(lit)
                model.AddBoolOr(span)
                cost_literals.append(lit)
                # Cost paid is max_cost * excess length.
                cost_coefficients.append(max_cost * (length - soft_max))

    # Just forbid any sequence of true variables with length hard_max + 1
    for start in range(len(works) - hard_max):
        model.AddBoolOr([works[i].Not() for i in range(start, start + hard_max + 1)])
    return cost_literals, cost_coefficients


def add_soft_sum_constraint(
    model,
    works,
    hard_min,
    soft_min,
    min_cost,
    soft_max,
    hard_max,
    max_cost,
    prefix,
):
    """sum constraint with soft and hard bounds.

    This constraint counts the variables assigned to true from works.
    If forbids sum < hard_min or > hard_max.
    Then it creates penalty terms if the sum is < soft_min or > soft_max.

    Args:
      model: the sequence constraint is built on this model.
      works: a list of Boolean variables.
      hard_min: any sequence of true variables must have a sum of at least
        hard_min.
      soft_min: any sequence should have a sum of at least soft_min, or a linear
        penalty on the delta will be added to the objective.
      min_cost: the coefficient of the linear penalty if the sum is less than
        soft_min.
      soft_max: any sequence should have a sum of at most soft_max, or a linear
        penalty on the delta will be added to the objective.
      hard_max: any sequence of true variables must have a sum of at most
        hard_max.
      max_cost: the coefficient of the linear penalty if the sum is more than
        soft_max.
      prefix: a base name for penalty variables.

    Returns:
      a tuple (variables_list, coefficient_list) containing the different
      penalties created by the sequence constraint.
    """
    cost_variables = []
    cost_coefficients = []
    sum_var = model.NewIntVar(hard_min, hard_max, "")
    # This adds the hard constraints on the sum.
    model.Add(sum_var == sum(works))

    # Penalize sums below the soft_min target.
    if soft_min > hard_min and min_cost > 0:
        delta = model.NewIntVar(-len(works), len(works), "")
        model.Add(delta == soft_min - sum_var)
        # TODO(user): Compare efficiency with only excess >= soft_min - sum_var.
        excess = model.NewIntVar(0, 7, prefix + ": under_sum")
        model.AddMaxEquality(excess, [delta, 0])
        cost_variables.append(excess)
        cost_coefficients.append(min_cost)

    # Penalize sums above the soft_max target.
    if soft_max < hard_max and max_cost > 0:
        delta = model.NewIntVar(-7, 7, "")
        model.Add(delta == sum_var - soft_max)
        excess = model.NewIntVar(0, 7, prefix + ": over_sum")
        model.AddMaxEquality(excess, [delta, 0])
        cost_variables.append(excess)
        cost_coefficients.append(max_cost)

    return cost_variables, cost_coefficients


OFF = 0
MORNING = 1
NIGHT = 2
UNFILLED = "Unfilled"
MAX_UNFILLED = 7


def solve_shift_scheduling(
        docs: list[str],
        # doc -> (min, max)
        desired_total_shifts: dict[str, tuple],
        # doc -> [(day, shift)]
        preferences: dict[str, list[tuple]],
        # doc -> [(day, shift)]
        unavailable: dict[str, list[tuple]],
        # doc -> [bool]
        prefer_double_shifts: dict[str, bool],
        max_unfilled: int,
        num_days: int,
):
    """Solves the shift scheduling problem."""
    # Data
    docs += [UNFILLED]
    desired_total_shifts[UNFILLED] = (0, max_unfilled)
    num_employees = len(docs)
    num_weeks = math.ceil(num_days / 7)
    shifts = ["O", "M", "N"]

    # Fixed assignment: (employee, shift, day).
    # This fixes the first 2 days of the schedule.
    #fixed_assignments = [
    # (0, 0, 0),
    # (1, 0, 0),
    # (2, 1, 0),
    # (3, 1, 0),
    # (4, 2, 0),
    # (5, 2, 0),
    # (6, 2, 3),
    # (7, 3, 0),
    # (0, 1, 1),
    # (1, 1, 1),
    # (2, 2, 1),
    # (3, 2, 1),
    # (4, 2, 1),
    # (5, 0, 1),
    # (6, 0, 1),
    # (7, 3, 1),
    #]

    # Request: (employee, shift, day, weight)
    # A negative weight indicates that the employee desire this assignment.
    #requests = [
    # Employee 3 does not want to work on the first Saturday (negative weight
    # for the Off shift).
    #(3, 0, 5, -2),
    # Employee 5 wants a night shift on the second Thursday (negative weight).
    #(5, 3, 10, -2),
    # Employee 2 does not want a night shift on the first Friday (positive
    # weight).
    #(2, 3, 4, 4),
    #]

    requests = []
    for doc in preferences:
        doc_id = docs.index(doc)
        for preference in preferences[doc]:
            requests += [(doc_id, preference[1], preference[0], -2)]

    for doc in unavailable:
        doc_id = docs.index(doc)
        for data in unavailable[doc]:
            requests += [(doc_id, data[1], data[0], 10)]

    # Shift constraints on continuous sequence :
    #     (shift, hard_min, soft_min, min_penalty,
    #             soft_max, hard_max, max_penalty)
    shift_constraints = [
        # One or two consecutive days of rest, this is a hard constraint.
        #(OFF, 1, 1, 0, 2, 2, 0),
        # between 2 and 3 consecutive days of night shifts, 1 and 4 are
        # possible but penalized.
        #(NIGHT, 1, 2, 20, 3, 4, 5),
    ]

    # Weekly sum constraints on shifts days:
    #     (shift, hard_min, soft_min, min_penalty,
    #             soft_max, hard_max, max_penalty)
    weekly_sum_constraints = [
        # Constraints on rests per week.
        #(OFF, 1, 2, 7, 2, 3, 4),
        # At least 1 night shift per week (penalized). At most 4 (hard).
        #(NIGHT, 0, 1, 3, 4, 4, 0),
    ]

    # Penalized transitions:
    #     (previous_shift, next_shift, penalty (0 means forbidden))
    penalized_transitions = [
        # Afternoon to night has a penalty of 4.
        #(2, 3, 4),
        # Night to morning is forbidden.
        (NIGHT, MORNING, 0),
    ]

    # daily demands for work shifts (morning, night) for each day
    # of the week starting on Monday.
    weekly_cover_demands = [
        (1, 1),  # Monday
        (1, 1),  # Tuesday
        (1, 1),  # Wednesday
        (1, 1),  # Thursday
        (1, 1),  # Friday
        (1, 1),  # Saturday
        (1, 1),  # Sunday
    ]

    # Penalty for exceeding the cover constraint per shift type.
    excess_cover_penalties = (2, 2, 5)

    #num_days = num_weeks * 7
    num_shifts = len(shifts)

    model = cp_model.CpModel()

    work = {}
    for e in range(num_employees):
        for s in range(num_shifts):
            for d in range(num_days):
                work[e, s, d] = model.NewBoolVar("work%i_%i_%i" % (e, s, d))

    # Linear terms of the objective in a minimization context.
    obj_int_vars: list[cp_model.IntVar] = []
    obj_int_coeffs: list[int] = []
    obj_bool_vars: list[cp_model.BoolVar] = []
    obj_bool_coeffs: list[int] = []

    # Exactly one shift per day.
    # TODO: support preference about multiple shifts when shifts span a day
    #for e in range(num_employees - 1):
    for doc in prefer_double_shifts:
        e = docs.index(doc)
        if not prefer_double_shifts[doc]:
            for d in range(num_days):
                model.AddExactlyOne(work[e, s, d] for s in range(num_shifts))

    # Fixed assignments.
    #for e, s, d in fixed_assignments:
    #    model.Add(work[e, s, d] == 1)

    # Employee requests
    for e, s, d, w in requests:
        if d >= num_days:
            continue
        obj_bool_vars.append(work[e, s, d])
        obj_bool_coeffs.append(w)

    # Shift constraints
    for ct in shift_constraints:
        shift, hard_min, soft_min, min_cost, soft_max, hard_max, max_cost = ct
        for e in range(num_employees):
            works = [work[e, shift, d] for d in range(num_days)]
            variables, coeffs = add_soft_sequence_constraint(
                model,
                works,
                hard_min,
                soft_min,
                min_cost,
                soft_max,
                hard_max,
                max_cost,
                "shift_constraint(employee %i, shift %i)" % (e, shift),
            )
            obj_bool_vars.extend(variables)
            obj_bool_coeffs.extend(coeffs)

    # Monthly sum constraints
    for e in range(num_employees):
        doc = docs[e]
        desired_min, desired_max = desired_total_shifts[doc]
        works = [work[e, shift, d] for d in range(num_days) for shift in range(1, num_shifts)]
        if e == num_employees - 1:
            soft_desired_max = desired_min
        else:
            soft_desired_max = desired_max
        variables, coeffs = add_soft_sum_constraint(
            model,
            works,
            desired_min, # hard min
            desired_min, # soft min
            2, # min cost
            soft_desired_max, # soft max
            desired_max, # hard max
            #int(desired_max * 1.2), # hard max
            2, # max cost
            "monthly_sum_constraint(employee %i)"
            % (e),
        )
        obj_int_vars.extend(variables)
        obj_int_coeffs.extend(coeffs)

    # Weekly sum constraints
    for ct in weekly_sum_constraints:
        shift, hard_min, soft_min, min_cost, soft_max, hard_max, max_cost = ct
        for e in range(num_employees):
            for w in range(num_weeks):
                works = [work[e, shift, d + w * 7] for d in range(7)]
                variables, coeffs = add_soft_sum_constraint(
                    model,
                    works,
                    hard_min,
                    soft_min,
                    min_cost,
                    soft_max,
                    hard_max,
                    max_cost,
                    "weekly_sum_constraint(employee %i, shift %i, week %i)"
                    % (e, shift, w),
                )
                obj_int_vars.extend(variables)
                obj_int_coeffs.extend(coeffs)

    # Penalized transitions
    for previous_shift, next_shift, cost in penalized_transitions:
        for e in range(num_employees):
            for d in range(num_days - 1):
                transition = [
                    work[e, previous_shift, d].Not(),
                    work[e, next_shift, d + 1].Not(),
                ]
                if cost == 0:
                    model.AddBoolOr(transition)
                else:
                    trans_var = model.NewBoolVar(
                        "transition (employee=%i, day=%i)" % (e, d)
                    )
                    transition.append(trans_var)
                    model.AddBoolOr(transition)
                    obj_bool_vars.append(trans_var)
                    obj_bool_coeffs.append(cost)

    # Cover constraints
    for s in range(1, num_shifts):
        for w in range(num_weeks):
            for d in range(7):
                if w * 7 + d >= num_days:
                    continue
                # Ignore unfilled shifts.
                works = [work[e, s, w * 7 + d] for e in range(num_employees)]
                # Ignore Off shift.
                min_demand = weekly_cover_demands[d][s - 1]
                worked = model.NewIntVar(min_demand, num_employees, "")
                model.Add(worked == sum(works))
                over_penalty = excess_cover_penalties[s - 1]
                if over_penalty > 0:
                    name = "excess_demand(shift=%i, week=%i, day=%i)" % (s, w, d)
                    excess = model.NewIntVar(0, num_employees - min_demand, name)
                    model.Add(excess == worked - min_demand)
                    obj_int_vars.append(excess)
                    obj_int_coeffs.append(over_penalty)

    # Objective
    model.Minimize(
        sum(obj_bool_vars[i] * obj_bool_coeffs[i] for i in range(len(obj_bool_vars)))
        + sum(obj_int_vars[i] * obj_int_coeffs[i] for i in range(len(obj_int_vars)))
    )

    #if output_proto:
    #    print("Writing proto to %s" % output_proto)
    #    with open(output_proto, "w") as text_file:
    #        text_file.write(str(model))

    # Solve the model.
    solver = cp_model.CpSolver()
    #if params:
    #    text_format.Parse(params, solver.parameters)
    #solution_printer = cp_model.ObjectiveSolutionPrinter()
    solution_printer = SolutionPrinter()
    status = solver.Solve(model, solution_printer)

    # print("Statistics")
    # print("  - status          : %s" % solver.StatusName(status))
    # print("  - conflicts       : %i" % solver.NumConflicts())
    # print("  - branches        : %i" % solver.NumBranches())
    # print("  - wall time       : %f s" % solver.WallTime())
    # print()

    # Print solution.
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        sys.stderr.write("\n")
        header = "          "
        for w in range(num_weeks):
            header += "M T W T F S S \n"
        sys.stderr.write(header)
        for e in range(num_employees):
            schedule = ""
            for d in range(num_days):
                for s in range(num_shifts):
                    if solver.BooleanValue(work[e, s, d]):
                        schedule += shifts[s] + " "
            sys.stderr.write("worker %i: %s\n" % (e, schedule))
        sys.stderr.write("\n")
        sys.stderr.write("Penalties:\n")
        for i, var in enumerate(obj_bool_vars):
            if solver.BooleanValue(var):
                penalty = obj_bool_coeffs[i]
                if penalty > 0:
                    #pass
                    sys.stderr.write(f"  {var.Name()} violated, penalty={penalty}\n")
                else:
                    #pass
                    sys.stderr.write(f"  {var.Name()} fulfilled, gain={-penalty}\n")

        for i, var in enumerate(obj_int_vars):
            if solver.Value(var) > 0:
                pass
                sys.stderr.write(
                    "  %s violated by %i, linear penalty=%i\n"
                    % (var.Name(), solver.Value(var), obj_int_coeffs[i])
                )

        schedule = []
        for d in range(num_days):
            shifts = [None, None]
            for s in range(1, num_shifts):
                for e in range(num_employees - 1):
                    if solver.BooleanValue(work[e, s, d]):
                        shifts[s - 1] = e
            schedule += [shifts]
        return schedule

    return []


def process_inputs(contents):
    inputs = json.loads(contents)
    docs = []
    preferences = {}
    unavailable = {}
    desired = {}
    prefer_double = {}
    for doc in inputs:
        name = doc["name"]
        docs += [name]
        # todo: supprt shift pefs
        preferences[name] = sum(map(lambda x: [(x, MORNING), (x, NIGHT)], doc["preferred"]), [])
        unavailable[name] = sum(map(lambda x: [(x, MORNING), (x, NIGHT)], doc["unavailable"]), [])
        desired[name] = (doc["min"], doc["max"])
        prefer_double[name] = doc["prefer_double"]
    return (docs, desired, preferences, unavailable, prefer_double)


def main():
    with open('inputs.json') as f:
        inputs = process_inputs(f.read())
    docs, desired, preferred, unavailable, prefer_double = inputs
    solve_shift_scheduling(docs, desired, preferred, unavailable, prefer_double, MAX_UNFILLED, 30)


if __name__ == "__main__":
    #app.run(main)
    main()
