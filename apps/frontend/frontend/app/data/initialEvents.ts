import { EventMap } from "../types";
import { RAINBOW } from "../utils/constants";

export const initialEvents: EventMap = {
  "2026-02-02": [
    {
      id: 1,
      kind: "event",
      allDay: false,
      startMin: 600,
      endMin: 630,
      title: "Training",
      color: RAINBOW[3],
      location: "Gym",
      notes: "",
    },
    {
      id: 2,
      kind: "event",
      allDay: false,
      startMin: 660,
      endMin: 720,
      title: "Transfer window opens",
      color: RAINBOW[0],
      location: "Office",
      notes: "",
    },
  ],
  "2026-02-03": [
    {
      id: 3,
      kind: "task",
      allDay: true,  // Tasks are always "all day"
      startMin: 0,   // Tasks don't have time
      endMin: 0,
      title: "First Division",
      color: RAINBOW[5],
      location: "Library",
      notes: "",
    },
  ],
};