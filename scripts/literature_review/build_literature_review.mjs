import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

process.on("uncaughtException", (error) => {
  console.error("UNCAUGHT", error?.message ?? error);
  console.error(String(error?.stack ?? "").split("\n").slice(0, 12).join("\n"));
  process.exit(1);
});
process.on("unhandledRejection", (error) => {
  console.error("UNHANDLED", error?.message ?? error);
  console.error(String(error?.stack ?? "").split("\n").slice(0, 12).join("\n"));
  process.exit(1);
});

const outputDir = "/Users/panyunzhu/Desktop/🪨African critical minerals/outputs";
const outputPath = `${outputDir}/非洲关键矿物价值链_文献综述.xlsx`;

const journalRows = [
  [2017, "Nature", "Mineral supply for sustainable development requires resource governance", "可持续发展所需的矿物供应需要资源治理", "如何在低碳转型和 SDGs 同时增加矿物需求的背景下，避免把矿物供应问题简单处理为地质储量或市场供给问题？", "Perspective/综合评述；把矿物供给、气候政策、SDGs、资源治理和地质科学政策放在同一框架讨论。", "矿物供应是实现气候目标和基础设施发展的前提，但供应本身会受到治理、勘探投资、社会许可和环境约束影响；资源治理能力决定矿产能否转化为可持续发展收益。", "可作为论文引言的总框架：把非洲关键矿物从“供应安全”转为“价值捕获与治理能力”。需要对话：其宏观治理视角。避开：不要停留在规范性治理倡议，应推进到矿山级价格差、成本和所有权证据。", "2017_Nature_Mineral supply for sustainable development requires resource governance.pdf"],
  [2018, "Nature Sustainability", "Sustainability of artisanal mining of cobalt in DR Congo", "刚果（金）手工钴矿的可持续性", "刚果（金）手工钴矿在全球电池供应链中的社会、健康和环境可持续性风险是什么？", "实地调查、环境/健康证据和供应链可持续性分析，聚焦 DRC 钴矿手工采矿。", "钴需求上升使 DRC 手工采矿暴露出职业健康、儿童劳动、污染和监管薄弱等问题；供应链尽责管理不能只看供给安全，还要面对上游社区成本。", "为你的“当地影响”模块提供社会风险背景，尤其是 DRC 铜钴样本。可改进：把社会风险与价格折价/财政捕获联系起来，说明当地承担外部性但租金未必留下。", "2018_Nature Sustainability_Sustainability of artisanal mining of cobalt in DR Congo.pdf"],
  [2020, "Nature Communications", "Renewable energy production will exacerbate mining threats to biodiversity", "可再生能源生产将加剧采矿对生物多样性的威胁", "能源转型所需矿物开采是否会扩大对保护地、关键生物多样性区域和荒野的压力？", "全球矿区空间数据叠加保护地、KBA 和荒野区域；用矿区密度衡量威胁强度。", "大量矿区与生物多样性优先区域重叠，且面向可再生能源材料的矿区占比很高；若缺乏空间规划，低碳转型可能转移而非消除环境损害。", "可用作生态外部性变量设计参考：矿山缓冲区与 protected areas/KBA/forest loss 叠加。避开：它关注生态威胁，不回答租金由谁捕获；你的贡献是把生态成本和价值流失放进同一矿山级框架。", "2020_Nature Communications_Renewable energy production will exacerbate mining threats to biodiversity.pdf"],
  [2020, "Nature Communications", "The social and environmental complexities of extracting energy transition metals", "开采能源转型金属的社会与环境复杂性", "能源转型金属资源是否集中在高 ESG 风险地区，不同金属的社会环境风险如何分布？", "构建全球复合 ESG 指标，并与 20 种金属矿业项目资源分布匹配。", "钴、铂族等关键金属很大比例位于高风险语境；资源丰富国家面临环境、社会和治理压力，低碳技术情景应纳入 ESG 约束。", "可借鉴其 ESG 风险指标组合，用来构造你的控制变量或“当地影响”板块。需要对话：将 ESG 风险从供应链脆弱性变量转化为资源国谈判能力/成本转嫁变量。", "2020_Nature Communications_The social and environmental complexities of extracting energy transition metals.pdf"],
  [2023, "Communications Earth & Environment", "Misalignment between national resource inventories and policy actions drives unevenness in the energy transition", "国家资源清单与政策行动错位导致能源转型不均衡", "拥有能源转型矿产资源的国家，其资源清单、项目准备度和开采政策是否匹配？", "整合 18 个资源国的矿业资产/项目数据与 2020-2023 年政策行动，比较 OECD 与非 OECD 国家。", "资源禀赋、项目准备度和政策行动并不总是对齐；OECD 国家政策响应更强，非 OECD 资源国可能因能力与政策错位在转型中处于不利位置。", "对你的样本选择有帮助：非洲资源国不只是“有矿”，还要看项目准备度、政策和市场接入。可改进：把政策错位进一步量化为 FOB 折价、加工能力缺失和财政捕获不足。", "2023_Communications Earth & Environment_Misalignment between national resource inventories and policy actions drives unevenness in the energy transition.pdf"],
  [2023, "Nature Sustainability", "Energy transition minerals and their intersection with land-connected peoples", "能源转型矿物与土地依附型人群的交叉", "能源转型矿产项目与原住民、农牧社区等土地依附型群体的空间重叠程度如何？", "全球能源转型矿产项目清单与土地连接型人群/原住民领地空间叠加分析。", "大量 ETM 项目与土地连接型人群存在交叉，能源转型的矿物扩张会带来土地权利、FPIC 和分配正义问题。", "为你的社会影响和社会许可部分提供空间方法。避开：不要只做权利受影响叙述；可将其转为“社会冲突/许可风险如何影响成本、延误和租金分配”的机制。", "2023_Nature Sustainability_Energy transition minerals and their intersection with land-connected peoples.pdf"],
  [2023, "Nature Sustainability", "Mineral security essential to achieving the Sustainable Development Goals", "矿物安全对实现可持续发展目标至关重要", "矿物安全如何支撑 SDGs，同时矿物开发又如何可能削弱可持续发展？", "概念框架/综合评述，连接矿物安全、供应链、资源治理和 SDGs。", "矿物安全不仅是消费国供应安全，也涉及生产国发展、安全、环境和社会目标；需要更平衡的全球治理。", "可作为论文理论部分的“矿物安全再定义”文献。需要对话：你的研究可把“生产国矿物安全”具体化为 FiscalCapture、PriceGap 和本地加工能力。", "2023_Nature Sustainability_Mineral security essential to achieving the Sustainable Development Goals.pdf"],
  [2024, "Nature Geoscience", "Regional rare-earth element supply and demand balanced with circular economy strategies", "通过循环经济策略平衡区域稀土供需", "循环经济、回收和区域化策略能否缓解稀土供需不平衡？", "区域供需建模、物质流/情景分析，评估循环经济对稀土供需缺口的缓解作用。", "回收、替代和循环策略可缓解部分区域稀土供需压力，但不能完全替代新矿开发；区域差异显著。", "对你研究的间接启发：下游回收/替代会影响长期租金空间和价格基准。近期 proposal 可少展开，避免偏离非洲矿山级价值捕获主线。", "2024_Nature Geoscience_Regional rare-earth element supply and demand balanced with circular economy strategies.pdf"],
  [2024, "Nature Sustainability", "Reducing supply risk of critical materials for clean energy via foreign direct investment", "通过外国直接投资降低清洁能源关键材料供应风险", "FDI 是否能够降低清洁能源关键材料供应风险，供应风险如何在投资网络中变化？", "构建关键材料供应风险与跨国直接投资网络/情景分析，考察投资来源和目的地组合。", "FDI 可以通过矿产资产布局影响供应风险，但也会改变控制权和收益分配；投资网络并不自动保证生产国获益。", "与你的所有权模块高度相关。可对话：它把 FDI 看作降低消费国风险的工具；你的研究应反问 FDI 是否加剧资源国租金外流、FOB 折价或税基侵蚀。", "2024_Nature Sustainability_Reducing supply risk of critical materials for clean energy via foreign direct investment.pdf"],
  [2024, "The Extractive Industries and Society", "Value addition for who? Challenges to local participation in downstream critical mineral ventures in Zambia", "为谁增值？赞比亚下游关键矿物项目中本地参与的挑战", "赞比亚推进关键矿物下游增值时，本地企业为何难以参与并分享收益？", "观点型案例研究；基于赞比亚专家访谈和政策/产业背景分析。", "外资在上游占主导、本地企业能力和融资不足、政策环境不完善，使“本地增值”容易变成外资主导的新环节，而非本地收益扩大。", "非常适合你的赞比亚案例。可用来支撑 H4：缺乏本地加工能力和本地企业参与会扩大价值链价差。可改进：用贸易价格、所有权和财政数据检验“为谁增值”。", "2024_The Extractive Industries and Society_Value addition for who Challenges to local participation in downstream critical mineral ventures in Zambia.pdf"],
  [2025, "Communications Earth & Environment", "Country's wealth is not associated with domestic control of metal ore extraction", "国家财富与金属矿石开采的本国控制并无关联", "国家财富是否对应更高的本国矿山控制权？海外矿山所有权是否转化为直接物质流？", "将多区域投入产出分析与 2000-2022 年公司所有权数据结合，为 159 个国家和 4 个世界区域构建金属开采控制图谱。", "本国财富与本土开采由本国控制的比例没有明显关联；海外所有权也未必带来物质流回流，市场力量可能压过公司控制。", "与你的“最终母公司/UBO 控制”模块直接对话。可借鉴企业所有权穿透与 Sankey 可视化；可改进：进一步看控制权是否影响非洲出口价格折价和租金捕获，而不只看控制比例。", "2025_Communications Earth & Environment_Country's wealth is not associated with domestic control of metal ore extraction.pdf"],
  [2025, "Nature Climate Change", "Navigating energy transition solutions for climate targets with minerals constraint", "在矿物约束下寻找实现气候目标的能源转型方案", "关键矿物短缺如何约束全球和区域能源转型路径？", "分析 IPCC AR6 的 557 条减排路径，使用 GREAT 模型评估 40 种矿物与 17 类能源技术的需求和短缺。", "许多路径在 2100 年前面临多种矿物短缺，发展中和资源脆弱地区更严重；减碳路径需要技术组合、资源约束和区域公平的共同优化。", "用于长期论文的需求侧背景，说明非洲矿物租金空间为何重要。近期 proposal 不宜深入模型，可引用为价格压力和战略重要性的外生背景。", "2025_Nature Climate Change_Navigating energy transition solutions for climate targets with minerals constraint.pdf"],
  [2025, "Nature Communications", "Critical mineral constraints pressure energy transition and trade toward the Paris Agreement climate goals", "关键矿物约束给实现巴黎协定目标的能源转型与贸易带来压力", "关键矿物供应、回收和技术进步约束如何改变中国能源转型、贸易需求和温升风险？", "将矿物约束纳入综合评估模型路径，设计原生供应、回收和技术进步情景。", "矿物约束可能显著压低光伏和风电装机，对碳中和路径和国际贸易产生压力；回收和技术进步可缓解但不能完全消除约束。", "可作为需求压力背景和矿物价格周期合理性的支撑。避开：它是中国/全球能源模型，不适合作为你的核心方法；你的核心应是非洲资源端如何捕获需求压力带来的租金。", "2025_Nature Communications_Critical mineral constraints pressure energy transition and trade toward the Paris Agreement climate goals.pdf"],
  [2025, "Nature Communications", "Sub-technology market share strongly affects critical material constraints in power system transitions", "子技术市场份额强烈影响电力系统转型中的关键材料约束", "不同光伏、风电等子技术市场份额如何改变关键材料需求和约束？", "电力系统转型情景下的 19 种关键材料需求建模，比较子技术市场份额变化。", "光伏和风电子技术组合显著改变镓、铽、锗、碲、铟、铀、铜等材料约束；技术路线本身会重塑矿物需求。", "可用于长期情景讨论：不同技术路线影响非洲矿物的未来租金。近期一个月版本可作为外生需求不确定性，避免展开复杂技术情景。", "2025_Nature Communications_Sub-technology market share strongly affects critical material constraints in power system transitions.pdf"],
  [2026, "Energy Research & Social Science", "Beyond geopolitics: Social license and supply chain risks of critical minerals", "超越地缘政治：关键矿物的社会许可与供应链风险", "谁定义关键矿物的“关键性”？社区和社会许可如何成为供应链风险因素？", "定性研究与 Ghana lithium 案例；从社会许可、FPIC、补偿和社区参与角度重构 criticality。", "关键性不能只由国家、产业和地缘政治定义；社区排斥、补偿不足和程序延迟会提高冲突成本、推迟项目并影响供应链可靠性。", "可用于你的 Ghana/锂或社会许可模块。对话点：把社会许可从规范风险转为可度量变量，例如项目延误、冲突事件、成本上升，并检验其与租金捕获/外资控制的关系。", "2026_Energy Research & Social Science_Beyond geopolitics Social license and supply chain risks of critical minerals.pdf"],
  [2026, "Nature Climate Change", "Deforestation-induced emissions from mining energy transition minerals", "能源转型矿物开采导致的森林砍伐排放", "能源转型矿物开采是否会造成可识别的森林损失和额外温室气体排放？", "将近 3000 个矿业项目与卫星森林变化数据结合，使用 staggered difference-in-differences 识别矿山导致的森林损失和排放。", "ETM 采矿在 10 km 缓冲区内造成持续森林损失，平均约 15 年内 20%；纳入砍伐排放后，采矿阶段碳足迹平均增加 63%。", "方法非常可用：矿山点位 + 卫星 forest loss + DID/缓冲区。可为你的生态社会影响模块提供严谨识别模板；近期版本可先做描述性 buffer 指标。", "2026_Nature Climate Change_Deforestation-induced emissions from mining energy transition minerals.pdf"],
];

const reportRows = [
  [2015, "FERDI", "系统回顾非洲矿产资源租金在政府和投资者之间如何分配，强调价格繁荣期资源租金增长并未同比转化为非洲政府税收。", "可用作“经济租金/租金分享”理论来源；提供租金、公平份额、矿业税制、资源租税等概念。方法上提醒不要只看矿价，要区分总租金、政府税收和投资者正常利润。", "2015_FERDI_What Do We Know about the Sharing of Mineral Resource Rent in Africa.pdf"],
  [2015, "ICTD", "与 FERDI 版本主题高度重合，讨论非洲矿产资源租金分享的理论、经验研究和知识缺口。", "可作为税收与租金捕获综述的补充引用；若正文篇幅有限，可与 FERDI 合并处理，避免重复引用。对你的方法启发是建立 FiscalCapture = Government revenue / Export value。", "2015_ICTD_What Do We Know about Mineral Resource Rent Sharing in Africa.pdf"],
  [2022, "PIIE", "讨论绿色能源关键矿物和稀土供应链由谁控制，强调直接所有权不足以识别真实控制，需要穿透多层股权和投票权。", "可用其 voting power/control index 思路改进你的 UBO 模块；数据方法启发：直接股东、最终母公司、注册地、投票权、控制链条要分开。可与 S&P Capital IQ、OpenCorporates、GLEIF 结合。", "2022_PIIE_Green Energy Depends on Critical Minerals Who Controls the Supply Chains.pdf"],
  [2023, "ECDPM", "评估非洲利用关键原材料发展锂电池价值链的机会和障碍，强调区域价值链、AfCFTA、产业政策、市场准入和地缘竞争。", "可用于本地加工/区域价值链背景；方法上可提取“区域价值链可行性”变量：加工能力、能源/基础设施、市场准入、政策协调、私营部门参与。", "2023_ECDPM_Green industrialisation Leveraging critical raw materials for an African battery value chain.pdf"],
  [2023, "IGF & OECD", "以铝土矿为例提出矿产品转让定价和矿物价格确定框架，服务发展中国家矿业税基保护。", "与你的几内亚铝土矿和转移定价主题直接相关；可借鉴可比非受控价格、矿石品位、水分/杂质、运费、加工费、市场基准调整等定价步骤，作为 PriceGap 分解框架。", "2023_IGF & OECD_Determining the Price of Minerals A transfer pricing framework for bauxite.pdf"],
  [2023, "UNCTAD", "讨论非洲关键矿物如何带来产业多元化机会，重点是中高技术供应链中的 linkages、pulling dynamics 和工业政策。", "可支撑你的 H4：缺乏本地加工能力导致价值链低位锁定。可用作变量/案例线索：前向后向联系、所有权结构、就业影响、产业政策能力、生产性转型。", "2023_UNCTAD_Critical Minerals and Routes to Diversification in Africa Linkages, Pulling Dynamics and Opportunities in Medium-High Tech Supply Chains.pdf"],
  [2024, "African Union", "Africa's Green Minerals Strategy / African Green Minerals Strategy，提出非洲围绕绿色矿物推进勘探、能力建设、价值链、本地增值和矿物治理。", "可作为政策框架和非洲联盟层面的规范基准；用于说明资源国目标是从原矿出口转向本地加工、区域工业化和矿物治理。可提取四大支柱作为政策变量编码框架。", "2024_African Union_Africa's Green Minerals Strategy.pdf"],
  [2025, "IGF", "讨论关键矿物价值增值中的税收设计，关注如何在加工、冶炼、增值政策中保护税基并避免低效激励。", "非常适合财政捕获和本地加工章节；可用来识别税收假期、出口限制、加工激励、转让定价、成本扣除、关联交易等风险。方法上提醒区分价值增值政策的财政收益和产业收益。", "2025_IGF_Tax Considerations for Critical Minerals Value Addition.pdf"],
  [2025, "OECD", "通过钴、锂、镍案例分析出口限制的贸易和国内影响，关注出口限制、下游加工、ESG 和贸易政策。", "可用于讨论出口限制是否能提高资源国价值捕获。方法上可借鉴案例比较：限制前后出口量/价格、下游投资、贸易转移、国内加工能力、全球供应链反应。", "2025_OECD_Trade and domestic effects of export restrictions Insights from case studies of cobalt, lithium and nickel.pdf"],
  [2026, "African Development Bank", "African Economic Outlook 2026 讨论碎片化世界中非洲发展融资，包含增长、融资缺口、外部融资、债务和发展资金动员背景。", "可用于宏观动机：非洲发展融资缺口和关键矿物作为替代融资来源。可与 FiscalCapture、出口收入、BoP 改善不足相连接；不宜作为矿山级数据来源。", "2026_African Development Bank_African Economic Outlook 2026 Mobilizing Africa's Development Financing at Scale in a Fragmented World.pdf"],
  [2026, "USGS", "Mineral Commodity Summaries 2026 提供全球矿产品产量、储量、价格、用途、进出口依赖和主要国家分布。", "核心数据手册：可用于铜、钴、锂、镍、石墨、锰、铝土矿、稀土、铂族等矿物的全球产量/储量背景、价格走势和主要生产国份额；适合做样本选择和宏观校准。", "2026_USGS_Mineral Commodity Summaries 2026.pdf"],
  [2026, "World Economic Forum", "文章提出非洲应通过本地加工、财政收入提升和区域一体化，将关键矿物转化为发展融资来源。", "可用于政策叙事和引言：非洲拥有大量关键矿物但货币化不足。可借用 1.6 万亿美元融资缺口、关键矿物收入潜力等论点，但应以 AfDB/USGS/官方数据交叉验证。", "2026_World Economic Forum_3 ways Africa can maximize the value of its critical minerals and finance its future.docx"],
  ["n.d.", "Cloudflare", "Security verification 页面，不是有效文献，可能是下载失败或网页反爬验证文件。", "不建议纳入综述或引用；保留在表中只是为了说明 literatures 目录中的全部文件已检查。", "n.d._Cloudflare_Security verification.html"],
];

const readmeRows = [
  ["工作簿说明", "本 Excel 根据 ResearchProposal 中的长期 Word 草案与近期 PDF proposal，围绕“非洲关键矿物价值链中的经济租金由谁捕获”组织文献。"],
  ["长期论文主线", "矿山-矿物-国家-年份面板；价格差、所有权穿透、离岸结构、财政捕获、本地加工和生态社会影响。"],
  ["近期一个月重点", "优先服务 JIMF proposal：LME/FOB/坑口价差、AISC/TCRC/Selling costs、S&P Capital IQ 矿山级数据、正常利润与经济租金剥离。"],
  ["分类口径", "Nature/Elsevier/Springer 等期刊文章进入“期刊论文”；机构报告、工作论文、政策文章进入“机构报告”。"],
  ["未纳入有效文献", ".DS_Store 是 macOS 系统文件；Cloudflare Security verification 是验证页，不是文献。Cloudflare 项已放入报告表并标注不可引用。"],
];

const workbook = Workbook.create();
const defaultSheet = workbook.worksheets.add("说明");
const journalSheet = workbook.worksheets.add("期刊论文");
const reportSheet = workbook.worksheets.add("机构报告");

function colName(n) {
  let s = "";
  while (n > 0) {
    const m = (n - 1) % 26;
    s = String.fromCharCode(65 + m) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

function writeSheet(sheet, headers, rows, widths) {
  const data = [headers, ...rows];
  const range = sheet.getRange(`A1:${colName(headers.length)}${data.length}`);
  range.values = data;
  range.format = {
    font: { name: "Aptos", size: 10, color: "#1F2937" },
    verticalAlignment: "top",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#D1D5DB" },
  };
  sheet.getRange(`A1:${colName(headers.length)}1`).format = {
    fill: "#1F4E78",
    font: { name: "Aptos", size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#D1D5DB" },
  };
  widths.forEach((width, idx) => {
    sheet.getRange(`${colName(idx + 1)}:${colName(idx + 1)}`).format.columnWidthPx = width;
  });
  sheet.getRange(`A1:${colName(headers.length)}1`).format.rowHeightPx = 44;
  if (rows.length) {
    sheet.getRange(`A2:${colName(headers.length)}${rows.length + 1}`).format.rowHeightPx = 128;
  }
}

writeSheet(
  defaultSheet,
  ["项目", "说明"],
  readmeRows,
  [170, 900],
);

writeSheet(
  journalSheet,
  ["年份", "期刊名称", "研究标题（英文）", "标题（中文）", "研究问题", "研究方法", "研究结论", "对我研究的启发", "源文件"],
  journalRows,
  [70, 170, 320, 260, 360, 360, 390, 480, 340],
);

writeSheet(
  reportSheet,
  ["年份", "机构", "报告主要内容", "和我研究相关的可用主要数据或方法学", "源文件"],
  reportRows,
  [70, 180, 520, 620, 380],
);

for (const sheet of [defaultSheet, journalSheet, reportSheet]) {
  sheet.getRange("A1:A1").format.horizontalAlignment = "center";
}

const journalUsed = await workbook.inspect({
  kind: "table",
  range: "期刊论文!A1:I6",
  include: "values",
  tableMaxRows: 6,
  tableMaxCols: 9,
});
console.log(journalUsed.ndjson);

const reportUsed = await workbook.inspect({
  kind: "table",
  range: "机构报告!A1:E6",
  include: "values",
  tableMaxRows: 6,
  tableMaxCols: 5,
});
console.log(reportUsed.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 50 },
  summary: "formula error scan",
});
console.log(errors.ndjson);

await workbook.render({ sheetName: "说明", range: "A1:B6", scale: 1 });
await workbook.render({ sheetName: "期刊论文", range: "A1:I8", scale: 1 });
await workbook.render({ sheetName: "机构报告", range: "A1:E8", scale: 1 });

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
