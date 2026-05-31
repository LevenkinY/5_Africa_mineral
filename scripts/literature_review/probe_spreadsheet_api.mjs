import { Workbook } from "@oai/artifact-tool";

const workbook = Workbook.create();
console.log(await workbook.help("worksheet range values formatting table export"));
