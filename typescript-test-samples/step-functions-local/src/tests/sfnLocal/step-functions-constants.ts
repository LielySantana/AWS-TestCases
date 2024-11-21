// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import fs from 'fs';
import path from 'path';

const EVENT_FILE: string = path.join(__dirname, "../../../events/sfn_valid_input.json");

export const StepFunctionsConstants = {
    mockFileHostPath: path.join(__dirname, '../../../statemachine/test/MockConfigFile.json') as string,
    mockFileContainerPath: "/home/stepfunctionslocal/MockConfigFile.json",
    DUMMY_ROLE: "arn:aws:iam::123456789012:role/DummyRole",
    EVENT_FILE: EVENT_FILE,
    STATE_MACHINE_ASL: fs.readFileSync(path.join(__dirname, "../../../statemachine/local_testing.asl.json")).toString(),
    STATE_MACHINE_NAME: "LocalTesting",
    EVENT_JSON_STRING: fs.readFileSync(EVENT_FILE).toString()
}