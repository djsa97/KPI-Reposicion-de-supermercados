import Foundation
import AppKit
import PDFKit
import Vision

struct OCRLine: Codable {
    let text: String
    let minX: Double
    let minY: Double
    let maxX: Double
    let maxY: Double
}

func renderPDFPage(pdfPath: String, pageIndex: Int, scale: CGFloat = 2.0) -> CGImage? {
    guard let document = PDFDocument(url: URL(fileURLWithPath: pdfPath)),
          let page = document.page(at: pageIndex) else {
        return nil
    }

    let bounds = page.bounds(for: .mediaBox)
    let width = Int(bounds.width * scale)
    let height = Int(bounds.height * scale)

    guard let colorSpace = CGColorSpace(name: CGColorSpace.sRGB),
          let context = CGContext(
            data: nil,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: 0,
            space: colorSpace,
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
          ) else {
        return nil
    }

    context.setFillColor(NSColor.white.cgColor)
    context.fill(CGRect(x: 0, y: 0, width: CGFloat(width), height: CGFloat(height)))

    context.saveGState()
    context.scaleBy(x: scale, y: scale)
    page.draw(with: .mediaBox, to: context)
    context.restoreGState()

    return context.makeImage()
}

func recognize(cgImage: CGImage) throws -> [OCRLine] {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = false
    request.recognitionLanguages = ["es-PY", "es-ES", "en-US"]

    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    try handler.perform([request])

    let observations = request.results ?? []
    return observations.compactMap { observation in
        guard let candidate = observation.topCandidates(1).first else {
            return nil
        }
        let bb = observation.boundingBox
        return OCRLine(
            text: candidate.string,
            minX: Double(bb.minX),
            minY: Double(bb.minY),
            maxX: Double(bb.maxX),
            maxY: Double(bb.maxY)
        )
    }
}

let args = CommandLine.arguments
guard args.count >= 3 else {
    fputs("usage: swift ocr_pdf_obs.swift <pdf_path> <page_index>\n", stderr)
    exit(1)
}

let pdfPath = args[1]
let pageIndex = Int(args[2]) ?? 0

guard let cgImage = renderPDFPage(pdfPath: pdfPath, pageIndex: pageIndex) else {
    fputs("failed to render pdf page\n", stderr)
    exit(2)
}

do {
    let lines = try recognize(cgImage: cgImage)
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    let data = try encoder.encode(lines)
    FileHandle.standardOutput.write(data)
} catch {
    fputs("ocr failed: \(error)\n", stderr)
    exit(3)
}
