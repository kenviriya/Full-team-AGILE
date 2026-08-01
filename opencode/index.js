import { tool } from "@opencode-ai/plugin/tool";

const UNSUPPORTED =
  "OpenCode provides the bundled portable skills, but this native plugin does not run the Claude-only Obsidian artifact, hook, agent-model, or release lifecycle.";

export default async function fullTeamAgile() {
  return {
    tool: {
      full_team_agile_status: tool({
        description:
          "Describe the Full-team-AGILE OpenCode integration and its unsupported Claude-only capabilities.",
        args: {},
        async execute() {
          return {
            title: "Full-team-AGILE OpenCode support",
            output: `${UNSUPPORTED}\n\nThe package includes the portable feature, sprint, and release skills for reuse; OpenCode's stable V1 plugin API does not register or transform them. Use the portable skills when your OpenCode setup supplies compatible delegation, durable artifact storage, and Git lifecycle support.`,
          };
        },
      }),
    },
  };
}

export { UNSUPPORTED };
