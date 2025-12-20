/**
 * Mock data for HACCP module demo
 * This provides realistic sample data for the 2-day demo shell
 */

// Mock sensor devices (for monitored temperature demo)
export const mockSensors = [
  {
    id: 1,
    sensor_id: "SENSOR-WI-001",
    outlet_id: 1,
    device_type: "cooler_temp",
    location_name: "Walk-in Cooler #1",
    threshold_min: 32,
    threshold_max: 38,
    last_reading: 36.2,
    last_reading_time: "2024-12-19T09:15:00Z",
    status: "pass"
  },
  {
    id: 2,
    sensor_id: "SENSOR-WI-002",
    outlet_id: 1,
    device_type: "cooler_temp",
    location_name: "Walk-in Cooler #2",
    threshold_min: 32,
    threshold_max: 38,
    last_reading: 37.1,
    last_reading_time: "2024-12-19T09:15:00Z",
    status: "pass"
  },
  {
    id: 3,
    sensor_id: "SENSOR-PREP-001",
    outlet_id: 1,
    device_type: "cooler_temp",
    location_name: "Prep Station Cooler",
    threshold_min: 32,
    threshold_max: 38,
    last_reading: 35.4,
    last_reading_time: "2024-12-19T09:15:00Z",
    status: "pass"
  },
  {
    id: 4,
    sensor_id: "SENSOR-BAR-001",
    outlet_id: 1,
    device_type: "cooler_temp",
    location_name: "Bar Cooler",
    threshold_min: 32,
    threshold_max: 38,
    last_reading: 41.2,
    last_reading_time: "2024-12-19T09:15:00Z",
    status: "fail"
  },
  {
    id: 5,
    sensor_id: "SENSOR-DES-001",
    outlet_id: 1,
    device_type: "cooler_temp",
    location_name: "Dessert Display Case",
    threshold_min: 32,
    threshold_max: 38,
    last_reading: 33.8,
    last_reading_time: "2024-12-19T09:15:00Z",
    status: "pass"
  }
];

export const mockChecklists = [
  {
    id: 1,
    name: "Morning Cooler Temperatures",
    description: "Check all walk-in coolers and freezers",
    record_tags: ["HACCP", "Daily", "Temperature"],
    created_at: "2024-12-15T08:00:00Z",
    is_active: true,
    checks: [
      {
        id: 1,
        check_type: "cooler_temp",
        name: "Walk-in Cooler #1",
        description: "Main prep cooler",
        order_index: 1,
        config: {
          threshold: 38,
          unit: "°F",
          comparison: "less_than"
        }
      },
      {
        id: 2,
        check_type: "cooler_temp",
        name: "Freezer #2",
        description: "Main storage freezer",
        order_index: 2,
        config: {
          threshold: 0,
          unit: "°F",
          comparison: "less_than"
        }
      },
      {
        id: 3,
        check_type: "task",
        name: "Check door seals",
        description: "Visually inspect all cooler door seals for damage",
        order_index: 3,
        config: {
          result_type: "boolean"
        }
      }
    ]
  },
  {
    id: 2,
    name: "Weekly Thermometer Calibration",
    description: "Verify all thermometers are accurate",
    record_tags: ["HACCP", "Weekly", "Equipment"],
    created_at: "2024-12-10T08:00:00Z",
    is_active: true,
    checks: [
      {
        id: 4,
        check_type: "thermometer_cal",
        name: "Digital Probes",
        description: "Test both digital probe thermometers",
        order_index: 1,
        config: {
          thermometers: [
            {
              name: "Probe #1",
              ice_water_threshold: 33,
              ice_water_comparison: "less_than",
              boiling_water_threshold: 210,
              boiling_water_comparison: "greater_than"
            },
            {
              name: "Probe #2",
              ice_water_threshold: 33,
              ice_water_comparison: "less_than",
              boiling_water_threshold: 210,
              boiling_water_comparison: "greater_than"
            }
          ]
        }
      }
    ]
  },
  {
    id: 3,
    name: "Monthly Kitchen Safety Meeting",
    description: "Document monthly safety meeting and training",
    record_tags: ["Training", "Monthly", "Safety"],
    created_at: "2024-12-01T08:00:00Z",
    is_active: true,
    checks: [
      {
        id: 5,
        check_type: "meeting_notes",
        name: "Safety Meeting Documentation",
        description: "Upload meeting notes and attendance",
        order_index: 1,
        config: {
          requires_file_upload: true,
          requires_attendance: true
        }
      },
      {
        id: 6,
        check_type: "task",
        name: "Review accident log",
        description: "Review and discuss any recent accidents",
        order_index: 2,
        config: {
          result_type: "boolean"
        }
      },
      {
        id: 7,
        check_type: "task",
        name: "Update safety posters",
        description: "Ensure all safety posters are current",
        order_index: 3,
        config: {
          result_type: "boolean"
        }
      }
    ]
  },
  {
    id: 4,
    name: "IoT Monitored Cooler Check",
    description: "Verify all IoT-monitored coolers are within safe temperature range",
    record_tags: ["HACCP", "Daily", "IoT", "Temperature"],
    created_at: "2024-12-15T08:00:00Z",
    is_active: true,
    checks: [
      {
        id: 8,
        check_type: "monitored_cooler_temps",
        name: "All Monitored Coolers",
        description: "Review sensor readings and verify all temperatures are within acceptable range",
        order_index: 1,
        config: {
          sensor_ids: [1, 2, 3, 4, 5], // References mockSensors array
          threshold_min: 32,
          threshold_max: 38,
          unit: "°F",
          verification_mode: "exception_only" // "view_only", "individual_confirmation", or "exception_only"
        }
      }
    ]
  }
];

export const mockAssignments = [
  {
    id: 1,
    checklist_id: 1,
    checklist_name: "Morning Cooler Temperatures",
    outlet_id: 1,
    outlet_name: "Downtown Kitchen",
    assigned_to: ["John Smith", "Sarah Chen"],
    recurrence: "daily",
    recurrence_config: { time: "09:00" },
    start_date: "2024-12-01",
    end_date: null,
    created_at: "2024-12-01T08:00:00Z"
  },
  {
    id: 2,
    checklist_id: 1,
    checklist_name: "Morning Cooler Temperatures",
    outlet_id: 2,
    outlet_name: "Westside Location",
    assigned_to: ["Mike Johnson"],
    recurrence: "daily",
    recurrence_config: { time: "08:30" },
    start_date: "2024-12-01",
    end_date: null,
    created_at: "2024-12-01T08:00:00Z"
  },
  {
    id: 3,
    checklist_id: 2,
    checklist_name: "Weekly Thermometer Calibration",
    outlet_id: 1,
    outlet_name: "Downtown Kitchen",
    assigned_to: ["Sarah Chen"],
    recurrence: "weekly",
    recurrence_config: { days: [1], time: "10:00" }, // Monday
    start_date: "2024-12-01",
    end_date: null,
    created_at: "2024-12-01T08:00:00Z"
  },
  {
    id: 4,
    checklist_id: 2,
    checklist_name: "Weekly Thermometer Calibration",
    outlet_id: 2,
    outlet_name: "Westside Location",
    assigned_to: ["Mike Johnson"],
    recurrence: "weekly",
    recurrence_config: { days: [1], time: "11:00" },
    start_date: "2024-12-01",
    end_date: null,
    created_at: "2024-12-01T08:00:00Z"
  },
  {
    id: 5,
    checklist_id: 3,
    checklist_name: "Monthly Kitchen Safety Meeting",
    outlet_id: null, // org-wide
    outlet_name: "All Outlets",
    assigned_to: ["John Smith", "Sarah Chen", "Mike Johnson"],
    recurrence: "monthly",
    recurrence_config: { day: 1, time: "14:00" }, // 1st of month
    start_date: "2024-12-01",
    end_date: null,
    created_at: "2024-12-01T08:00:00Z"
  },
  {
    id: 6,
    checklist_id: 4,
    checklist_name: "IoT Monitored Cooler Check",
    outlet_id: 1,
    outlet_name: "Downtown Kitchen",
    assigned_to: ["John Smith", "Sarah Chen"],
    recurrence: "daily",
    recurrence_config: { time: "09:30" },
    start_date: "2024-12-15",
    end_date: null,
    created_at: "2024-12-15T08:00:00Z"
  }
];

export const mockInstances = [
  {
    id: 1,
    assignment_id: 1,
    checklist_id: 1,
    checklist_name: "Morning Cooler Temperatures",
    outlet_id: 1,
    outlet_name: "Downtown Kitchen",
    due_date: "2024-12-19",
    status: "pending",
    assigned_to: ["John Smith", "Sarah Chen"],
    created_at: "2024-12-19T00:00:00Z"
  },
  {
    id: 2,
    assignment_id: 2,
    checklist_id: 1,
    checklist_name: "Morning Cooler Temperatures",
    outlet_id: 2,
    outlet_name: "Westside Location",
    due_date: "2024-12-19",
    status: "completed",
    completed_at: "2024-12-19T08:45:00Z",
    completed_by: "Mike Johnson",
    assigned_to: ["Mike Johnson"],
    created_at: "2024-12-19T00:00:00Z"
  },
  {
    id: 3,
    assignment_id: 1,
    checklist_id: 1,
    checklist_name: "Morning Cooler Temperatures",
    outlet_id: 1,
    outlet_name: "Downtown Kitchen",
    due_date: "2024-12-18",
    status: "completed",
    completed_at: "2024-12-18T09:15:00Z",
    completed_by: "Sarah Chen",
    assigned_to: ["John Smith", "Sarah Chen"],
    created_at: "2024-12-18T00:00:00Z",
    has_corrective_action: true // Failed temp
  },
  {
    id: 4,
    assignment_id: 6,
    checklist_id: 4,
    checklist_name: "IoT Monitored Cooler Check",
    outlet_id: 1,
    outlet_name: "Downtown Kitchen",
    due_date: "2024-12-19",
    status: "pending",
    assigned_to: ["John Smith", "Sarah Chen"],
    created_at: "2024-12-19T00:00:00Z"
  }
];

export const mockResults = [
  // Results for instance #2 (completed today - all passed)
  {
    id: 1,
    instance_id: 2,
    check_id: 1,
    check_name: "Walk-in Cooler #1",
    check_type: "cooler_temp",
    result_data: {
      temperature: 36.5,
      timestamp: "2024-12-19T08:40:00Z"
    },
    requires_corrective_action: false,
    recorded_at: "2024-12-19T08:40:00Z",
    recorded_by: "Mike Johnson"
  },
  {
    id: 2,
    instance_id: 2,
    check_id: 2,
    check_name: "Freezer #2",
    check_type: "cooler_temp",
    result_data: {
      temperature: -5.2,
      timestamp: "2024-12-19T08:42:00Z"
    },
    requires_corrective_action: false,
    recorded_at: "2024-12-19T08:42:00Z",
    recorded_by: "Mike Johnson"
  },
  {
    id: 3,
    instance_id: 2,
    check_id: 3,
    check_name: "Check door seals",
    check_type: "task",
    result_data: {
      completed: true
    },
    requires_corrective_action: false,
    recorded_at: "2024-12-19T08:45:00Z",
    recorded_by: "Mike Johnson"
  },
  // Results for instance #3 (yesterday - failed temp)
  {
    id: 4,
    instance_id: 3,
    check_id: 1,
    check_name: "Walk-in Cooler #1",
    check_type: "cooler_temp",
    result_data: {
      temperature: 42.3,
      timestamp: "2024-12-18T09:10:00Z"
    },
    requires_corrective_action: true,
    corrective_action_notes: "Temperature above safe threshold. Checked door seal - found gap. Called maintenance. Adjusted thermostat down 2 degrees. Will recheck in 1 hour.",
    recorded_at: "2024-12-18T09:10:00Z",
    recorded_by: "Sarah Chen"
  },
  {
    id: 5,
    instance_id: 3,
    check_id: 2,
    check_name: "Freezer #2",
    check_type: "cooler_temp",
    result_data: {
      temperature: -8.1,
      timestamp: "2024-12-18T09:12:00Z"
    },
    requires_corrective_action: false,
    recorded_at: "2024-12-18T09:12:00Z",
    recorded_by: "Sarah Chen"
  },
  {
    id: 6,
    instance_id: 3,
    check_id: 3,
    check_name: "Check door seals",
    check_type: "task",
    result_data: {
      completed: true
    },
    requires_corrective_action: false,
    recorded_at: "2024-12-18T09:15:00Z",
    recorded_by: "Sarah Chen"
  }
];

// Helper function to get instances for a specific status
export const getInstancesByStatus = (status) => {
  return mockInstances.filter(instance => instance.status === status);
};

// Helper function to get due instances count
export const getDueInstancesCount = () => {
  return mockInstances.filter(instance => instance.status === 'pending').length;
};

// Helper function to get completed instances count for a date range
export const getCompletedInstancesCount = (days = 7) => {
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - days);

  return mockInstances.filter(instance => {
    if (instance.status !== 'completed') return false;
    const completedDate = new Date(instance.completed_at);
    return completedDate >= cutoffDate;
  }).length;
};

// Helper function to get results for an instance
export const getResultsForInstance = (instanceId) => {
  return mockResults.filter(result => result.instance_id === instanceId);
};

// Stats for dashboard
export const mockStats = {
  totalChecklists: mockChecklists.length,
  activeAssignments: mockAssignments.length,
  dueToday: getDueInstancesCount(),
  completedThisWeek: getCompletedInstancesCount(7),
  overdue: 0 // For demo purposes
};
