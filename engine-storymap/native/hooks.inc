static const unsigned char expected0[]={0x81,0xec,0x00,0x02,0x00,0x00};
static const unsigned char expected1[]={0x56,0x8b,0x74,0x24,0x08};
static const unsigned char expected2[]={0x51,0x53,0x55,0x8b,0x6c,0x24,0x10};
static const unsigned char expected3[]={0x56,0x57,0x8b,0x7c,0x24,0x0c};
static const unsigned char expected4[]={0x53,0x55,0x56,0x8b,0x74,0x24,0x10};
static const unsigned char expected5[]={0x53,0x55,0x8b,0x6c,0x24,0x0c};
static const unsigned char expected6[]={0xdd,0x44,0x24,0x1c,0x83,0xec,0x5c};
static const unsigned char expected7[]={0x81,0xec,0x94,0x00,0x00,0x00};
static const unsigned char expected8[]={0x56,0x57,0xe8,0x29,0x39,0x00,0x00};
static const unsigned char expected9[]={0x81,0xec,0x00,0x02,0x00,0x00};
static const unsigned char expected10[]={0xa1,0x7c,0x04,0x48,0x00};
static const unsigned char expected11[]={0xa1,0x78,0xac,0x56,0x00};
static const unsigned char expected12[]={0x53,0x55,0x56,0x8b,0x74,0x24,0x10};
static const unsigned char expected13[]={0x53,0x55,0x56,0x8b,0x74,0x24,0x10};
static const unsigned char expected14[]={0x8b,0x15,0x6c,0x3a,0x4f,0x00};
static const unsigned char expected15[]={0xa1,0xa4,0xe1,0x56,0x00};
static const unsigned char expected16[]={0xa1,0xa4,0xe1,0x56,0x00};
static const unsigned char expected17[]={0x8b,0x44,0x24,0x08,0x53};
static const unsigned char expected18[]={0x83,0xec,0x24,0x53,0x55};
static const unsigned char expected19[]={0x6a,0x40,0xff,0x74,0x24,0x0c};
static const unsigned char expected20[]={0xa0,0x84,0x27,0x51,0x00};
static const unsigned char expected21[]={0x55,0x8b,0xec,0x83,0xec,0x0c};
static const unsigned char expected22[]={0x8b,0x44,0x24,0x0c,0x81,0xec,0x9c,0x00,0x00,0x00};   // 0x413ab0 text line (text4k.inc)
static const unsigned char expected23[]={0x8b,0x44,0x24,0x5c,0x85,0xc0};                      // 0x4141d8 inside 0x413ab0: a new glyph is averaged
static const unsigned char expected24[]={0x51,0x8b,0x4c,0x24,0x08};                           // 0x4147e0 cached glyph to the line
static const unsigned char expected25[]={0x53,0x8b,0x5c,0x24,0x08};                           // 0x440840 line onto the page
static const unsigned char expected26[]={0x53,0x8b,0x5c,0x24,0x0c};                           // 0x4146e0 glyph into the engine's cache
static Hook hooks[]={
{0x417950,6,expected0,(void*)Load,(void**)&oldLoad},
{0x43afb0,5,expected1,(void*)Free,(void**)&oldFree},
{0x442870,7,expected2,(void*)Copy,(void**)&oldCopy},
{0x442c60,6,expected3,(void*)Swap,(void**)&oldSwap},
{0x443180,7,expected4,(void*)Alpha,(void**)&oldAlpha},
{0x440640,6,expected5,(void*)Mask,(void**)&oldMask},
{0x4434e0,7,expected6,(void*)Transform,(void**)&oldTransform},
{0x43f4a0,6,expected7,(void*)Mode,nullptr},
{0x437ad0,7,expected8,(void*)Render,(void**)&oldRender},
{0x4180a0,6,expected9,(void*)LoadDirect,(void**)&oldLoadDirect},
{0x43f9f0,5,expected10,(void*)Layout,(void**)&oldLayout},
{0x4403a0,5,expected11,(void*)GetMode,nullptr},
{0x41c130,7,expected12,(void*)VarFind,(void**)&oldVarFind},
{0x41c310,7,expected13,(void*)VarWrite,(void**)&oldVarWrite},
{0x41c230,6,expected14,(void*)VarHash,(void**)&oldVarHash},
{0x420390,5,expected15,(void*)SeenGet,(void**)&oldSeenGet},
{0x420260,5,expected16,(void*)SeenSet,(void**)&oldSeenSet},
{0x41b560,5,expected17,(void*)Input,(void**)&oldInput},
{0x40b260,5,expected18,(void*)FCLoop,(void**)&fcOldLoop},
{0x449ca9,6,expected19,(void*)FCFopen,(void**)&fcOldFopen},
{0x4220b0,5,expected20,(void*)FCEnginePath,(void**)&fcOldPath},
{0x449f56,6,expected21,(void*)ExactCompare,(void**)&oldExactCompare},
{0x413ab0,10,expected22,(void*)TextLine,(void**)&oldTextLine},
{0x4141d8,6,expected23,(void*)GlyphDoneStub,(void**)&glyphDoneBack},
{0x4147e0,5,expected24,(void*)GlyphPlace,(void**)&oldGlyphPlace},
{0x440840,5,expected25,(void*)LineBlend,(void**)&oldLineBlend},
{0x4146e0,5,expected26,(void*)GlyphStore,(void**)&oldGlyphStore},
};
