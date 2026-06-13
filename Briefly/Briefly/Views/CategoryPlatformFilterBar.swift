import SwiftUI

// MARK: - FilterDropdown

enum FilterDropdown: Equatable {
    case category, platform
}

// MARK: - Localization Helpers

private var isKorean: Bool {
    Locale.current.language.languageCode?.identifier == "ko"
}

func filterL(_ ko: String, _ en: String) -> String { isKorean ? ko : en }

func filterCategoryLabel(_ value: String) -> String {
    guard isKorean else { return value }
    switch value {
    case "Tech":      return "기술"
    case "Business":  return "비즈니스"
    case "Essays":    return "에세이"
    case "Research":  return "연구"
    case "Lifestyle": return "라이프스타일"
    case "News":      return "뉴스"
    case "Culture":   return "문화"
    case "Other":     return "기타"
    default:          return value
    }
}

// MARK: - CategoryPlatformFilterBar

struct CategoryPlatformFilterBar<Content: View>: View {
    let availableCategories: [String]
    let availableDomains: [String]
    @Binding var selectedCategories: Set<String>
    @Binding var selectedDomains: Set<String>
    @Binding var activeDropdown: FilterDropdown?
    var topPadding: CGFloat = 0
    @ViewBuilder let content: () -> Content

    private var categoryChipLabel: String {
        selectedCategories.isEmpty
            ? filterL("카테고리", "Category")
            : selectedCategories.sorted().map { filterCategoryLabel($0) }.joined(separator: ", ")
    }

    private var domainChipLabel: String {
        selectedDomains.isEmpty
            ? filterL("플랫폼", "Platform")
            : selectedDomains.sorted().joined(separator: ", ")
    }

    var body: some View {
        VStack(spacing: 0) {
            chipRow
            content()
                .overlay(alignment: .topLeading) { dropdownOverlay }
        }
    }

    private var chipRow: some View {
        HStack(spacing: 8) {
            FilterDropdownChip(
                label: categoryChipLabel,
                isActive: !selectedCategories.isEmpty,
                isOpen: activeDropdown == .category
            ) {
                withAnimation(.easeInOut(duration: 0.15)) {
                    activeDropdown = activeDropdown == .category ? nil : .category
                }
            }
            FilterDropdownChip(
                label: domainChipLabel,
                isActive: !selectedDomains.isEmpty,
                isOpen: activeDropdown == .platform
            ) {
                withAnimation(.easeInOut(duration: 0.15)) {
                    activeDropdown = activeDropdown == .platform ? nil : .platform
                }
            }
            Spacer()
        }
        .padding(.horizontal, 16)
        .padding(.top, topPadding)
        .padding(.bottom, 8)
    }

    @ViewBuilder
    private var dropdownOverlay: some View {
        if let active = activeDropdown {
            ZStack(alignment: .topLeading) {
                Color.clear
                    .contentShape(Rectangle())
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .onTapGesture {
                        withAnimation(.easeInOut(duration: 0.15)) { activeDropdown = nil }
                    }
                dropdownCard(for: active)
                    .frame(maxWidth: 220, alignment: .leading)
                    .padding(.horizontal, 16)
                    .padding(.top, 4)
                    .transition(.opacity.combined(with: .scale(scale: 0.95, anchor: .topLeading)))
            }
        }
    }

    private func dropdownCard(for kind: FilterDropdown) -> some View {
        let items: [String] = kind == .category ? availableCategories : availableDomains
        let selectedSet: Set<String> = kind == .category ? selectedCategories : selectedDomains
        let makeLabel: (String) -> String = kind == .category ? { filterCategoryLabel($0) } : { $0 }

        return VStack(alignment: .leading, spacing: 0) {
            Button {
                withAnimation(.easeInOut(duration: 0.15)) {
                    if kind == .category { selectedCategories = [] } else { selectedDomains = [] }
                    activeDropdown = nil
                }
            } label: {
                HStack {
                    Text(filterL("전체", "All"))
                        .font(.system(size: 14, weight: .medium))
                        .foregroundStyle(selectedSet.isEmpty ? Color.brieflyPrimary500 : Color.brieflyTextPrimary)
                    Spacer()
                    if selectedSet.isEmpty {
                        Image(systemName: "checkmark")
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(Color.brieflyPrimary500)
                    }
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 11)
            }
            .buttonStyle(.plain)

            ForEach(items, id: \.self) { item in
                Divider().padding(.horizontal, 8)
                Button {
                    withAnimation(.easeInOut(duration: 0.15)) {
                        if kind == .category {
                            if selectedCategories.contains(item) { selectedCategories.remove(item) }
                            else { selectedCategories.insert(item) }
                        } else {
                            if selectedDomains.contains(item) { selectedDomains.remove(item) }
                            else { selectedDomains.insert(item) }
                        }
                    }
                } label: {
                    HStack {
                        Text(makeLabel(item))
                            .font(.system(size: 14))
                            .foregroundStyle(selectedSet.contains(item) ? Color.brieflyPrimary500 : Color.brieflyTextPrimary)
                        Spacer()
                        if selectedSet.contains(item) {
                            Image(systemName: "checkmark")
                                .font(.system(size: 12, weight: .semibold))
                                .foregroundStyle(Color.brieflyPrimary500)
                        }
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 11)
                }
                .buttonStyle(.plain)
            }
        }
        .background(Color.brieflyBgSurface)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .shadow(color: .black.opacity(0.12), radius: 8, x: 0, y: 4)
    }
}

// MARK: - FilterDropdownChip

struct FilterDropdownChip: View {
    let label: String
    let isActive: Bool
    let isOpen: Bool
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 4) {
                Text(label)
                    .font(.system(size: 13, weight: .medium))
                    .lineLimit(1)
                Image(systemName: isOpen ? "chevron.up" : "chevron.down")
                    .font(.system(size: 10, weight: .semibold))
            }
            .foregroundStyle(isActive || isOpen ? Color.white : Color.brieflyTextPrimary)
            .padding(.horizontal, 12)
            .padding(.vertical, 7)
            .background(isActive || isOpen ? Color.brieflyPrimary500 : Color.brieflyBgSurface)
            .clipShape(Capsule())
            .overlay(
                Capsule().stroke(
                    isActive || isOpen ? Color.clear : Color.brieflyBorder,
                    lineWidth: 1
                )
            )
        }
        .buttonStyle(.plain)
        .animation(.easeInOut(duration: 0.15), value: isActive)
        .animation(.easeInOut(duration: 0.15), value: isOpen)
    }
}
